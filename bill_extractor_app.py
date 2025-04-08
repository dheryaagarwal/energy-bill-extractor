import streamlit as st
import fitz  # PyMuPDF
import re

def extract_fields(text):
    # Flatten PDF text
    clean_text = ' '.join(text.split())

    # Regex based on layout seen in screenshots
    month = re.search(r'Month\s*([A-Z]{3}-\d{4})', clean_text)
    units = re.search(r'Units\s*consumed\s*([\d,]+)', clean_text)
    sanctioned = re.search(r'Load\s*Sanctioned\s*(\d+\.?\d*)', clean_text)
    contract = re.search(r'Contract\s*Demand\s*(\d+\.?\d*)', clean_text)
    max_demand = re.search(r'Maximum\s*Demand\s*(\d+\.?\d*)', clean_text)

    return {
        "Month": month.group(1) if month else "Not Found",
        "Units Consumed": units.group(1).replace(",", "") if units else "Not Found",
        "Sanctioned Load (kW)": sanctioned.group(1) if sanctioned else "Not Found",
        "Contract Demand (kW)": contract.group(1) if contract else "Not Found",
        "Maximum Demand (kW)": max_demand.group(1) if max_demand else "Not Found"
    }

# Streamlit UI
st.set_page_config(page_title="Energy Bill Extractor", layout="centered")
st.title("🔍 Energy Bill PDF Extractor")
st.write("Upload one or more electricity bill PDFs to extract: Month, Units Consumed, Sanctioned Load, Contract Demand, and Max Demand.")

uploaded_files = st.file_uploader("Upload PDF bills", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        result = extract_fields(text)

        with st.expander(f"📄 Details for {uploaded_file.name}"):
            for k, v in result.items():
                st.markdown(f"**{k}**: {v}")
