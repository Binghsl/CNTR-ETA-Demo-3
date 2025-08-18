from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import pandas as pd
from io import BytesIO
from playwright.async_api import async_playwright

app = FastAPI()


@app.get("/")
def status():
    return {"status": "ETA backend is running"}


# ONE B/L Tracker Function (with iframe handling)
async def track_one_bl(mbl: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://ecomm.one-line.com/one-ecom/manage-shipment/cargo-tracking")

        # Wait for iframe and get inside
        await page.wait_for_selector("iframe")
        frame = page.frame_locator("iframe").first

        # Wait and interact inside the iframe
        await frame.locator("input#blNo").wait_for(timeout=20000)
        await frame.locator("input#blNo").fill(mbl)
        await frame.get_by_role("button", name="Track").click()

        # Wait for the result
        try:
            await frame.wait_for_selector("div:has-text('Vessel/Voyage')", timeout=15000)
            eta_element = frame.locator("text=Arrival").first
            parent = eta_element.locator("xpath=..")
            eta = await parent.locator("div").nth(1).inner_text()
        except:
            eta = "Not Found"

        await browser.close()
        return eta.strip()


# Upload and process Excel file
@app.post("/track")
async def upload_excel(file: UploadFile = File(...)):
    df = pd.read_excel(BytesIO(file.file.read()))
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
