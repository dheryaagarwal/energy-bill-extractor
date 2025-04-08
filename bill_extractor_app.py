import streamlit as st
import fitz  # PyMuPDF
import re

def extract_fields(text):
    """
    Extract the following fields from the PDF text:
      - Month                 (e.g., MAR-2025)
      - Units Consumed        (e.g., 4018)
      - Load Sanctioned (kW)  (e.g., 35.0)
      - Contract Demand (kW)  (e.g., 35.0)
      - Maximum Demand (kW)   (e.g., 21.94)
    """
    # Split text into non-empty, stripped lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # ----------------------------------------------------------------
    # (Optional) Debugging: Uncomment to see how lines are extracted.
    # ----------------------------------------------------------------
    # st.write("DEBUG: PDF lines -->")
    # for idx, line in enumerate(lines):
    #     st.write(f"[{idx}] {line}")
    # st.write("---")

    # Prepare default results
    results = {
        "Month": "Not Found",
        "Units Consumed": "Not Found",
        "Load Sanctioned (kW)": "Not Found",
        "Contract Demand (kW)": "Not Found",
        "Maximum Demand (kW)": "Not Found"
    }

    #
    # 1) UPPER-SECTION FIELDS
    #
    # Look for lines containing numeric values + "KW" for Load & Contract Demand.
    kw_values = []
    for line in lines:
        # Example match: "35.0 KW"
        # We'll capture the numeric part (35.0)
        m_kw = re.search(r'(\d+\.\d+|\d+)\s*KW', line, re.IGNORECASE)
        if m_kw:
            kw_values.append(m_kw.group(1))

    # Usually, the first two KW matches are:
    #   1) Load Sanctioned
    #   2) Contract Demand
    if len(kw_values) >= 2:
        results["Load Sanctioned (kW)"] = kw_values[0]
        results["Contract Demand (kW)"] = kw_values[1]

    # For Maximum Demand, sometimes it's just a decimal/float on its own line
    # or preceded by "Maximum Demand". We try line by line:
    for line in lines:
        lower_line = line.lower()
        if "maximum demand" in lower_line:
            # Example: "Maximum Demand 21.94"
            m_md = re.search(r'maximum\s+demand\s+(\d+\.\d+|\d+)', line, re.IGNORECASE)
            if m_md:
                results["Maximum Demand (kW)"] = m_md.group(1)
                break
        else:
            # If we see a line with only a decimal (e.g., "21.94"),
            # we can pick that up as a fallback.
            if re.fullmatch(r'\d+\.\d+', line):
                results["Maximum Demand (kW)"] = line
                break

    #
    # 2) LOWER-SECTION FIELDS: Month & Units Consumed
    #
    # Approach: first line-by-line. If not found, fallback to a text-wide regex.

    # (a) Line-by-Line: Month
    for line in lines:
        if "month" in line.lower():
            # Example: "MAR-2025MonthSSZ5 - 5 - 3372042572"
            m_month = re.search(r'([A-Z]{3}-\d{4})', line)
            if m_month:
                results["Month"] = m_month.group(1)
                break

    # (b) Line-by-Line: Units Consumed
    for line in lines:
        if "units consumed" in line.lower():
            # Example from your PDF:
            # "4,01803-Apr-2025 Units consumedBill Date"
            # We'll match a pattern that can capture 4,018 or 4018
            m_units = re.search(r'(\d{1,3}(?:,\d{3})+|\d+)', line)
            if m_units:
                # Remove commas to get an integer-like string
                results["Units Consumed"] = m_units.group(1).replace(",", "")
            break

    # (c) Fallback #1: If Month is still "Not Found"
    if results["Month"] == "Not Found":
        # Regex across the entire text for something like "MAR-2025" near "Month"
        # or anywhere if we know the PDF always has e.g. "MAR-2025"
        match_fallback_month = re.search(r'[A-Z]{3}-\d{4}', text)
        if match_fallback_month:
            results["Month"] = match_fallback_month.group(0)

    # (d) Fallback #2: If Units Consumed is still "Not Found"
    if results["Units Consumed"] == "Not Found":
        # Try searching the entire text for "Units consumed" plus a number
        # e.g., "Units consumedBill Date" might appear with no space
        match_fallback_units = re.search(
            r'Units\s*consumed.*?(\d{1,3}(?:,\d{3})+|\d+)', 
            text, 
            flags=re.IGNORECASE | re.DOTALL
        )
        if match_fallback_units:
            results["Units Consumed"] = match_fallback_units.group(1).replace(",", "")

    return results

# -----------------------------------------------------------------------------
# STREAMLIT APP
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Energy Bill Extractor", layout="centered")
st.title("🔍 Energy Bill PDF Extractor (Debugged)")

st.write("""
Upload one or more electricity bill PDFs to extract:

- **Month** (e.g., MAR-2025)
- **Units Consumed** (e.g., 4018)
- **Load Sanctioned (kW)**
- **Contract Demand (kW)**
- **Maximum Demand (kW)**
""")

uploaded_files = st.file_uploader("Upload PDF bills", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            # Read entire PDF
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            raw_text = ""
            for page in doc:
                raw_text += page.get_text()
            doc.close()

            # Extract fields
            results = extract_fields(raw_text)

        # Display in an expander
        with st.expander(f"Results for {uploaded_file.name}"):
            st.markdown(f"**Month:** {results['Month']}")
            st.markdown(f"**Units Consumed:** {results['Units Consumed']}")
            st.markdown(f"**Load Sanctioned (kW):** {results['Load Sanctioned (kW)']}")
            st.markdown(f"**Contract Demand (kW):** {results['Contract Demand (kW)']}")
            st.markdown(f"**Maximum Demand (kW):** {results['Maximum Demand (kW)']}")
