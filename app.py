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
        await page.goto("https://ecomm.one-line.com/one-ecom/manage-shipment/cargo-tracking")

        # Wait for the correct input box to appear and fill it
        await page.locator("input#blNo").wait_for(timeout=15000)
        await page.fill("input#blNo", mbl)

        # Click the 'Track' button
        await page.get_by_role("button", name="Track").click()

        try:
            # Wait for result to load by checking for presence of ETA section
            await page.wait_for_selector("text=Arrival", timeout=20000)
            eta_element = await page.locator("div:has-text('Arrival') + div").first
            eta = await eta_element.inner_text()
        except Exception:
            eta = "Not Found"

        await browser.close()
        return eta.strip()

@app.post("/track")
async def upload_excel(file: UploadFile = File(...)):
    df = pd.read_excel(BytesIO(await file.read()))
    results = []

    for _, row in df.iterrows():
        sci = row.get("SCI")
        carrier = str(row.get("CARRIER")).strip().upper()
        mbl = str(row.get("Master BL")).strip()

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
