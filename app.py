
import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.set_page_config(page_title="Container ETA Tracker", layout="centered")
st.title("📦 Container ETA Tracker")

# File upload
file = st.file_uploader("Upload Excel file with columns: SCI, CARRIER, Master BL", type=["xlsx"])

if file:
    st.success("✅ File uploaded successfully.")

    # Send to backend
    try:
        with st.spinner("🔍 Tracking ETA..."):
            response = requests.post(
                "https://cntr-eta-demo-3.onrender.com/track",  # ← Replace with your real backend URL
                files={"file": (file.name, file.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )

        if response.status_code == 200:
            result_df = pd.read_excel(BytesIO(response.content))
            st.success("📄 ETA Data Retrieved:")
            st.dataframe(result_df)

            # Download button
            st.download_button(
                label="⬇️ Download Results as Excel",
                data=response.content,
                file_name="ETA_Results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error(f"❌ Failed to retrieve ETA. Status code: {response.status_code}")
            st.text(response.text)

    except Exception as e:
        st.exception(e)
