import streamlit as st
import fitz  # PyMuPDF
import re

def parse_month(lines):
    """
    Extract 'Month' from a line containing 'Bill month'
    or any pattern like 'May-2024' or 'MAR-2025'
    """
    # 1) Check for "Bill month" lines
    for line in lines:
        lower_line = line.lower()
        if "bill month" in lower_line:
            # e.g., "Bill month : May-2024"
            # We'll match something like "XXXX-YYYY"
            m = re.search(r'([A-Za-z]{3,}-\d{4})', line)
            if m:
                return m.group(1).strip()

    # 2) Fallback: any line that has something like "May-2024" or "MAR-2025"
    for line in lines:
        m = re.search(r'([A-Za-z]{3,}-\d{4})', line)
        if m:
            return m.group(1).strip()

    return "Not Found"


def parse_units_consumed(lines):
    """
    Extract 'Units Consumed' from possible lines:
      - "Units consumed"
      - "Net Units Supplied"
      - "Total Units"
    """
    # 1) Check lines for "units consumed"
    for line in lines:
        if "units consumed" in line.lower():
            # e.g., "4,01803-Apr-2025 Units consumedBill Date"
            m = re.search(r'(\d{1,3}(?:,\d{3})+|\d+)', line)
            if m:
                return m.group(1).replace(",", "")

    # 2) Check lines for "net units supplied"
    for line in lines:
        if "net units supplied" in line.lower():
            # e.g., "Net Units Supplied 28261.00000"
            m = re.search(r'(\d+(?:\.\d+)?)', line)
            if m:
                # e.g., "28261.00000" -> "28261"
                return m.group(1).replace(".00000", "").replace(",", "")

    # 3) Check lines for "total units"
    for line in lines:
        if "total units" in line.lower():
            # e.g., "Total Units 28261.00000"
            m = re.search(r'(\d+(?:\.\d+)?)', line)
            if m:
                return m.group(1).replace(".00000", "").replace(",", "")

    return "Not Found"


def parse_load_sanctioned(lines):
    """
    Extract 'Load Sanctioned' if there's a line containing that phrase.
    If the new PDF only mentions 'Cont. Demand', we skip or fallback to Not Found.
    """
    for line in lines:
        lower_line = line.lower()
        if "load sanctioned" in lower_line:
            # e.g., "Load Sanctioned 35.0 KW"
            m = re.search(r'(\d+(?:\.\d+)?)\s*(kw|kva)?', line, re.IGNORECASE)
            if m:
                return m.group(1)
    return "Not Found"


def parse_contract_demand(lines):
    """
    Extract 'Contract Demand' from either 'Contract Demand' or 'Cont. Demand' lines.
    e.g., "Cont. Demand 120 KVA"
    """
    for line in lines:
        lower_line = line.lower()
        if "cont. demand" in lower_line or "contract demand" in lower_line:
            m = re.search(r'(\d+(?:\.\d+)?)\s*(kw|kva)?', line, re.IGNORECASE)
            if m:
                return m.group(1)
    return "Not Found"


def parse_max_demand(lines):
    """
    Extract 'Maximum Demand' from lines containing:
      - "Maximum Demand"
      - "Max Demand"
      - "Net Max Demand"
    e.g., "Net Max Demand 108.00000"
    """
    # 1) Check for lines with "Net Max Demand"
    for line in lines:
        if "net max demand" in line.lower():
            # e.g., "Net Max Demand 108.00000"
            m = re.search(r'net\s+max\s+demand\s+(\d+(?:\.\d+)?)', line.lower())
            if m:
                return m.group(1).replace(".00000", "")
            # If not in that exact format, do a more flexible pattern
            # capturing the first float after "Net Max Demand"
            m2 = re.search(r'net\s+max\s+demand\s+(\d+(?:\.\d+))', line.lower())
            if m2:
                return m2.group(1)
            # Or any float on that same line
            m3 = re.search(r'(\d+\.\d+)', line)
            if m3:
                return m3.group(1)

    # 2) Check for "Maximum Demand" or "Max Demand"
    for line in lines:
        if "maximum demand" in line.lower() or "max demand" in line.lower():
            m_md = re.search(r'(?:maximum|max)\s+demand[:\s-]*([\d\.]+)', line, re.IGNORECASE)
            if m_md:
                return m_md.group(1).replace(".00000", "")
            # fallback to any float in that line
            m2 = re.search(r'(\d+\.\d+)', line)
            if m2:
                return m2.group(1)

    # 3) If still not found, maybe there's a line that's just a decimal
    for line in lines:
        if re.fullmatch(r'\d+\.\d+', line):
            return line.strip()

    return "Not Found"


def extract_fields(raw_text):
    """
    Returns a dictionary with:
      - Month
      - Units Consumed
      - Load Sanctioned
      - Contract Demand
      - Maximum Demand
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    results = {
        "Month": parse_month(lines),
        "Units Consumed": parse_units_consumed(lines),
        "Load Sanctioned": parse_load_sanctioned(lines),
        "Contract Demand": parse_contract_demand(lines),
        "Maximum Demand": parse_max_demand(lines)
    }
    return results


# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="Energy Bill Extractor", layout="centered")
st.title("🔍 Energy Bill PDF Extractor (Multi-format)")

st.write("""
Upload one or more electricity bill PDFs to extract:

1. **Month**  
2. **Units Consumed**  
3. **Load Sanctioned**  
4. **Contract Demand**  
5. **Maximum Demand**  
""")

uploaded_files = st.file_uploader("Upload PDF bills", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            raw_text = ""
            for page in doc:
                raw_text += page.get_text()
            doc.close()

            results = extract_fields(raw_text)

        with st.expander(f"Results for {uploaded_file.name}"):
            st.markdown(f"**Month:** {results['Month']}")
            st.markdown(f"**Units Consumed:** {results['Units Consumed']}")
            st.markdown(f"**Load Sanctioned:** {results['Load Sanctioned']}")
            st.markdown(f"**Contract Demand:** {results['Contract Demand']}")
            st.markdown(f"**Maximum Demand:** {results['Maximum Demand']}")
