import streamlit as st
import fitz  # PyMuPDF
import re

# Set up the app
st.set_page_config(page_title="Energy Bill Extractor", layout="centered")
st.title("Energy Bill Extractor")
st.write("Upload one or more electricity bill PDFs to extract details.")

# File uploader
uploaded_files = st.file_uploader("Upload PDF bills", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = doc[0].get_text()
        doc.close()

        # Better patterns based on real bill
        month = re.search(r'Bill Date\s*\n(\d{2}-[A-Za-z]{3}-\d{4})', text)
        units = re.search(r'Units consumed.*?(\d{3,5})', text)
        sanctioned = re.search(r'Load Sanctioned\s*\n?(\d{1,5}\.?\d*)', text)
        contract = re.search(r'Contract Demand\s*\n?(\d{1,5}\.?\d*)', text)
        max_demand = re.search(r'Maximum\s+Demand\s*\n?(\d{1,5}\.?\d*)', text)

        # Clean results
        results = {
            "Month": month.group(1) if month else "Not Found",
            "Units Consumed": units.group(1) if units else "Not Found",
            "Sanctioned Load (kW)": sanctioned.group(1) if sanctioned else "Not Found",
            "Contract Demand (kW)": contract.group(1) if contract else "Not Found",
            "Maximum Demand (kW)": max_demand.group(1) if max_demand else "Not Found"
        }

        # Show results in expandable box
        with st.expander(f"Details for {uploaded_file.name}"):
            for key, value in results.items():
                st.markdown(f"**{key}**: {value}")
