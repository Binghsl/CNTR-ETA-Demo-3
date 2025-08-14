
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import pandas as pd
from io import BytesIO
from playwright.async_api import async_playwright

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ETA backend is running"}

async def track_one_bl(mbl: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://ecomm.one-line.com/one-ecom/searchContainer")
        await page.get_by_placeholder("B/L or Booking or Container No").fill(mbl)
        await page.get_by_role("button", name="Track").click()
        await page.wait_for_timeout(5000)
        content = await page.content()

        eta = "Not Found"
        try:
            if "ETA" in content:
                element = await page.query_selector("//div[contains(text(), 'ETA')]/following-sibling::div")
                eta = await element.inner_text() if element else "ETA not found"
        except:
            pass
        await browser.close()
        return eta.strip()

@app.post("/track")
async def upload_excel(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        return {"error": f"Failed to read Excel file: {str(e)}"}

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
