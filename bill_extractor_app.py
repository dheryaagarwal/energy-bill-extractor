import streamlit as st
import fitz  # PyMuPDF

def extract_fields(text):
    results = {
        "Month": "Not Found",
        "Units Consumed": "Not Found",
        "Sanctioned Load (kW)": "Not Found",
        "Contract Demand (kW)": "Not Found",
        "Maximum Demand (kW)": "Not Found"
    }

    lines = text.split('\n')

    for line in lines:
        lower_line = line.lower()

        if "month" in lower_line and results["Month"] == "Not Found":
            match = re.search(r'month\s*[:\-]?\s*([A-Z]{3}-\d{4})', line, re.IGNORECASE)
            if match:
                results["Month"] = match.group(1).strip()

        if "units consumed" in lower_line and results["Units Consumed"] == "Not Found":
            match = re.search(r'units\s*consumed\s*[:\-]?\s*([\d,]+)', line, re.IGNORECASE)
            if match:
                results["Units Consumed"] = match.group(1).replace(",", "").strip()

        if "load sanctioned" in lower_line and results["Sanctioned Load (kW)"] == "Not Found":
            match = re.search(r'load\s*sanctioned\s*[:\-]?\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                results["Sanctioned Load (kW)"] = match.group(1).strip()

        if "contract demand" in lower_line and results["Contract Demand (kW)"] == "Not Found":
            match = re.search(r'contract\s*demand\s*[:\-]?\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                results["Contract Demand (kW)"] = match.group(1).strip()

        if "maximum demand" in lower_line and results["Maximum Demand (kW)"] == "Not Found":
            match = re.search(r'maximum\s*demand\s*[:\-]?\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                results["Maximum Demand (kW)"] = match.group(1).strip()

    return results

# Streamlit App Setup
st.set_page_config(page_title="Energy Bill Extractor", layout="centered")
st.title("🔍 Energy Bill PDF Extractor")
st.write("Upload one or more electricity bill PDFs to extract Month, Units Consumed, Load Details.")

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
