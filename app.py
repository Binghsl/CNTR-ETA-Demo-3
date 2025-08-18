from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import pandas as pd
from io import BytesIO
from playwright.async_api import async_playwright

app = FastAPI()

@app.get("/")
def status():
    return {"status": "ETA backend is running"}


async def track_one_bl(mbl: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://ecomm.one-line.com/one-ecom/manage-shipment/cargo-tracking", timeout=60000)

        # 🔄 Click to trigger the dynamic textarea input to load
        try:
            await page.click("div.search_box_input")  # selector that triggers the textarea to appear
        except Exception as e:
            print(f"Warning: Could not click to activate input field: {e}")

        # ✅ Wait for the textarea and fill in the Master BL number
        await page.wait_for_selector("textarea#searchName", timeout=10000)
        await page.fill("textarea#searchName", mbl)

        # 🟢 Click the Search button
        try:
            await page.click("button:has-text('Search')")
        except Exception:
            # Fallback to clicking the first button if needed
            buttons = await page.query_selector_all("button")
            if buttons:
                await buttons[0].click()

        # 🟢 Wait for tracking info and extract ETA
        try:
            await page.wait_for_selector("text=Vessel/Voyage", timeout=30000)
            eta_element = await page.locator("xpath=//div[contains(text(), 'Arrival')]/following-sibling::div[1]").nth(0)
            eta = await eta_element.inner_text()
        except Exception:
            eta = "Not Found"

        await browser.close()
        return eta.strip()


@app.post("/track")
async def upload_excel(file: UploadFile = File(...)):
    contents = await file.read()
    df = pd.read_excel(BytesIO(contents))
    df.columns = [str(col).strip().upper() for col in df.columns]
    results = []

    for _, row in df.iterrows():
        sci = row.get("SCI")
        carrier = str(row.get("CARRIER") or "").strip().upper()
        mbl = str(row.get("MASTER BL") or "").strip()

        if carrier == "ONE" and mbl:
            try:
                eta = await track_one_bl(mbl)
                results.append({
                    "SCI": sci,
                    "CARRIER": carrier,
                    "Master BL": mbl,
                    "ETA": eta,
                    "Raw Info": f"ETA: {eta}"
                })
            except Exception as e:
                results.append({
                    "SCI": sci,
                    "CARRIER": carrier,
                    "Master BL": mbl,
                    "ETA": "ERROR",
                    "Raw Info": str(e)
                })

    output_df = pd.DataFrame(results)
    stream = BytesIO()
    output_df.to_excel(stream, index=False)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ETA_Results.xlsx"}
    )
