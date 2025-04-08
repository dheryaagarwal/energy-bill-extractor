import streamlit as st
import fitz  # PyMuPDF
import re

# Set page config
st.set_page_config(page_title="Energy Bill Info Extractor", layout="centered")

st.title("Multi PDF Energy Bill Extractor")
st.write("Upload one or more electricity bill PDFs to extract and view billing details.")

# Upload multiple PDFs
uploaded_files = st.file_uploader("Upload your bills (PDF format)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        # Extract text from first page
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = doc[0].get_text()
        doc.close()

        # Extract data using regex
        month = re.search(r'Month\s*([A-Z]+-\d{4})', text)
        units = re.search(r'Units consumed.*?(\d+)', text)
        sanctioned = re.search(r'Load Sanctioned\s*(\d+\.?\d*)', text)
        contract = re.search(r'Contract Demand\s*(\d+\.?\d*)', text)
        max_demand = re.search(r'Maximum\s+Demand\s*(\d+\.?\d*)', text)

        # Display data for each file
        with st.expander(f"Details for {uploaded_file.name}"):
            st.markdown(f"**Month**: {month.group(1) if month else 'Not Found'}")
            st.markdown(f"**Units Consumed**: {units.group(1) if units else 'Not Found'}")
            st.markdown(f"**Sanctioned Load (kW)**: {sanctioned.group(1) if sanctioned else 'Not Found'}")
            st.markdown(f"**Contract Demand (kW)**: {contract.group(1) if contract else 'Not Found'}")
            st.markdown(f"**Maximum Demand (kW)**: {max_demand.group(1) if max_demand else 'Not Found'}")
            