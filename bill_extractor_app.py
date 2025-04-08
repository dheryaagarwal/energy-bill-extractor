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

    # Read line by line for accurate matching
    lines = text.split('\n')

    for i, line in enumerate(lines):
        line_clean = line.strip().lower()

        if "month" in line_clean and results["Month"] == "Not Found":
            results["Month"] = lines[i+1].strip()

        if "units consumed" in line_clean and results["Units Consumed"] == "Not Found":
            results["Units Consumed"] = lines[i+1].strip().replace(",", "")

        if "load sanctioned" in line_clean and results["Sanctioned Load (kW)"] == "Not Found":
            results["Sanctioned Load (kW)"] = lines[i+1].strip().split()[0]

        if "contract demand" in line_clean and results["Contract Demand (kW)"] == "Not Found":
            results["Contract Demand (kW)"] = lines[i+1].strip().split()[0]

        if "maximum demand" in line_clean and results["Maximum Demand (kW)"] == "Not Found":
            results["Maximum Demand (kW)"] = lines[i+1].strip().split()[0]

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
