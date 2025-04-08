import streamlit as st
import fitz  # PyMuPDF
import re

def extract_fields(text):
    """
    Extracts the desired fields from the PDF text.
    
    Returns a dictionary containing:
      - Month (e.g., MAR-2025)
      - Units Consumed (e.g., 4018)
      - Load Sanctioned (kW) (e.g., 35.0)
      - Contract Demand (kW) (e.g., 35.0)
      - Maximum Demand (kW) (e.g., 21.94)
    """
    # Split text into non-empty, stripped lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Debug: Uncomment the following line to display all extracted lines
    # st.write("Debug - PDF Lines:", lines)
    
    # Set default values
    results = {
        "Month": "Not Found",
        "Units Consumed": "Not Found",
        "Load Sanctioned (kW)": "Not Found",
        "Contract Demand (kW)": "Not Found",
        "Maximum Demand (kW)": "Not Found"
    }
    
    # ---------------
    # UPPER SECTION
    # ---------------
    # Look for lines containing "KW" to extract Load Sanctioned & Contract Demand.
    kw_values = []
    for line in lines:
        m = re.search(r'(\d+\.\d+)\s*KW', line, re.IGNORECASE)
        if m:
            kw_values.append(m.group(1))
    # Assuming the first two KW values are:
    #   1. Load Sanctioned and 2. Contract Demand
    if len(kw_values) >= 2:
        results["Load Sanctioned (kW)"] = kw_values[0]
        results["Contract Demand (kW)"] = kw_values[1]
    
    # For Maximum Demand, look for a line that is just a number (and not containing "KW")
    for line in lines:
        if "kw" in line.lower():
            continue
        # Match a decimal number on its own (e.g., "21.94")
        if re.fullmatch(r'\d+\.\d+', line):
            results["Maximum Demand (kW)"] = line
            break

    # ----------------
    # LOWER SECTION
    # ----------------
    # For Units Consumed, find the line containing "Units consumed"
    # Example: "4,01803-Apr-2025 Units consumedBill Date"
    for line in lines:
        if "units consumed" in line.lower():
            m = re.search(r'([\d,]+)', line)
            if m:
                # Remove commas from the number (e.g., "4,018" -> "4018")
                results["Units Consumed"] = m.group(1).replace(",", "")
            break  # Assume only one relevant occurrence
    
    # For Month, search for a pattern like "MAR-2025" on a line containing "month"
    for line in lines:
        if "month" in line.lower():
            m = re.search(r'([A-Z]{3}-\d{4})', line)
            if m:
                results["Month"] = m.group(1)
            break

    return results

# -----------------------------
# Streamlit App Interface
# -----------------------------
st.set_page_config(page_title="Energy Bill Extractor", layout="centered")
st.title("🔍 Energy Bill PDF Extractor")
st.write("""
Upload one or more electricity bill PDFs to extract the following fields:

- **Month** (e.g., MAR-2025)
- **Units Consumed** (numerical value)
- **Load Sanctioned (kW)**
- **Contract Demand (kW)**
- **Maximum Demand (kW)**
""")

uploaded_files = st.file_uploader("Upload PDF bills", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            # Open the PDF and extract all text from all pages
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            results = extract_fields(text)
            
            with st.expander(f"Results for {uploaded_file.name}"):
                st.markdown(f"**Month:** {results['Month']}")
                st.markdown(f"**Units Consumed:** {results['Units Consumed']}")
                st.markdown(f"**Load Sanctioned (kW):** {results['Load Sanctioned (kW)']}")
                st.markdown(f"**Contract Demand (kW):** {results['Contract Demand (kW)']}")
                st.markdown(f"**Maximum Demand (kW):** {results['Maximum Demand (kW)']}")
