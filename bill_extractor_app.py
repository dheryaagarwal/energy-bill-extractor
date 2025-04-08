import streamlit as st
import fitz  # PyMuPDF
import re

# --- Helper Functions ---

def get_first_numeric(line: str) -> str:
    """
    Attempt to get a numeric value from a line.
    If a comma is present and the number appears to be thousand‐formatted,
    we try to use the portion before any trailing extra digits.
    Otherwise, we return the first numeric chunk.
    """
    # Try to find a number that is NOT immediately followed by more digits after a comma
    # (This pattern helps avoid matching just the "4" from "4,01803")
    match = re.search(r'(\d{1,3},\d{3})(?!\d)', line)
    if match:
        return match.group(1).replace(",", "")
    # Fallback: return the first numeric sequence
    match = re.search(r'(\d+(?:\.\d+)?)', line)
    if match:
        return match.group(1)
    return ""

def parse_units_consumed_custom(text_line: str) -> str:
    """
    Specifically extract Units Consumed from a line that may be merged with a date.
    Remove any date pattern (e.g. "03-Apr-2025") first,
    then search for a 3- to 6-digit number.
    """
    # Remove potential date strings like "03-Apr-2025"
    cleaned = re.sub(r'\d{1,2}-[A-Za-z]{3}-\d{4}', '', text_line)
    # Now search for a group of 3 to 6 digits
    match = re.search(r'\b(\d{3,6})\b', cleaned)
    if match:
        return match.group(1)
    return ""

def next_non_empty_line(lines, i):
    """Return the next non-empty line after index i, or an empty string if none."""
    j = i + 1
    while j < len(lines):
        if lines[j].strip():
            return lines[j]
        j += 1
    return ""

# --- Line-by-Line Parsing ---

def parse_line_by_line(lines):
    """
    Go through the lines one by one, checking for our key labels.
    If a value isn’t on the same line as the label, check the very next non-empty line.
    Returns a dictionary with partial results.
    """
    results = {
        "Month": None,
        "Units Consumed": None,
        "Load Sanctioned": None,
        "Contract Demand": None,
        "Maximum Demand": None,
    }

    for i, line in enumerate(lines):
        lower_line = line.lower()

        # --- Month ---
        if "month" in lower_line and results["Month"] is None:
            m = re.search(r'([A-Za-z]{3,}-\d{4})', line)
            if m:
                results["Month"] = m.group(1)
            else:
                nxt = next_non_empty_line(lines, i)
                m2 = re.search(r'([A-Za-z]{3,}-\d{4})', nxt)
                if m2:
                    results["Month"] = m2.group(1)

        # --- Units Consumed ---
        if "units consumed" in lower_line and results["Units Consumed"] is None:
            # Merge current line with the next non-empty line to capture jammed text
            merged = line + " " + next_non_empty_line(lines, i)
            val = parse_units_consumed_custom(merged)
            if val:
                results["Units Consumed"] = val
            else:
                nxt = next_non_empty_line(lines, i)
                val2 = parse_units_consumed_custom(nxt)
                if val2:
                    results["Units Consumed"] = val2

        # Also look for fallback labels like "total units" or "net units supplied"
        if any(keyword in lower_line for keyword in ["total units", "net units supplied"]) and results["Units Consumed"] is None:
            m = re.search(r'\b(\d{3,6})\b', line)
            if m:
                results["Units Consumed"] = m.group(1)

        # --- Load Sanctioned ---
        if "load sanctioned" in lower_line and results["Load Sanctioned"] is None:
            val = get_first_numeric(line)
            if not val:
                val = get_first_numeric(next_non_empty_line(lines, i))
            if val:
                results["Load Sanctioned"] = val

        # --- Contract Demand ---
        if ("contract demand" in lower_line or "cont. demand" in lower_line) and results["Contract Demand"] is None:
            val = get_first_numeric(line)
            if not val:
                val = get_first_numeric(next_non_empty_line(lines, i))
            if val:
                results["Contract Demand"] = val

        # --- Maximum Demand ---
        if any(x in lower_line for x in ["maximum demand", "max demand", "net max demand"]) and results["Maximum Demand"] is None:
            val = get_first_numeric(line)
            if not val:
                val = get_first_numeric(next_non_empty_line(lines, i))
            if val:
                results["Maximum Demand"] = val

    return results

# --- Fallback: Text-Wide Regex ---

def fallback_in_whole_text(text):
    """
    If the line-by-line method fails for any field, run a broad regex search
    on the entire text for that field.
    """
    t = text.replace(",", "")  # remove commas for simplicity
    fallback_results = {
        "Month": None,
        "Units Consumed": None,
        "Load Sanctioned": None,
        "Contract Demand": None,
        "Maximum Demand": None,
    }

    m_month = re.search(r'([A-Za-z]{3,}-\d{4})', t)
    if m_month:
        fallback_results["Month"] = m_month.group(1)

    m_units = re.search(r'(\d{3,6})\s*(?:units\s*consumed)', t, re.IGNORECASE)
    if m_units:
        fallback_results["Units Consumed"] = m_units.group(1)
    if not fallback_results["Units Consumed"]:
        m_u2 = re.search(r'(?:total units|net units supplied)\s*(\d{3,6})', t, re.IGNORECASE)
        if m_u2:
            fallback_results["Units Consumed"] = m_u2.group(1)

    m_ls = re.search(r'load\s*sanctioned\s*(\d+(?:\.\d+)?)', t, re.IGNORECASE)
    if m_ls:
        fallback_results["Load Sanctioned"] = m_ls.group(1)

    m_cd = re.search(r'(?:contract demand|cont\. demand)\s*(\d+(?:\.\d+)?)', t, re.IGNORECASE)
    if m_cd:
        fallback_results["Contract Demand"] = m_cd.group(1)

    m_md = re.search(r'(?:maximum demand|max demand|net max demand)\s*(\d+(?:\.\d+)?)', t, re.IGNORECASE)
    if m_md:
        fallback_results["Maximum Demand"] = m_md.group(1)

    return fallback_results

# --- Main Extraction Function: Combine Both Approaches ---

def extract_fields(pdf_text):
    lines = [ln.strip() for ln in pdf_text.splitlines() if ln.strip()]
    line_results = parse_line_by_line(lines)
    fallback_results = fallback_in_whole_text(pdf_text)
    final = {}
    for field in ["Month", "Units Consumed", "Load Sanctioned", "Contract Demand", "Maximum Demand"]:
        val_line = line_results.get(field)
        val_fb = fallback_results.get(field)
        if val_line:
            final[field] = val_line
        elif val_fb:
            final[field] = val_fb
        else:
            final[field] = "Not Found"
        if isinstance(final[field], str):
            final[field] = final[field].replace(".00000", "")
    return final

# --- STREAMLIT APP INTERFACE ---

st.set_page_config(page_title="Energy Bill Extractor", layout="centered")
st.title("Energy Bill PDF Extractor (Final Robust Version)")
st.write("""
This app extracts the following fields:
- **Month** (e.g., MAR-2025)
- **Units Consumed** (e.g., 4018)
- **Load Sanctioned** (e.g., 35.0)
- **Contract Demand** (e.g., 35.0)
- **Maximum Demand** (e.g., 21.94)

It uses both a line-by-line method (with next-line lookup) and a fallback text-wide regex.
""")

uploaded_files = st.file_uploader("Upload PDF(s)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for f in uploaded_files:
        with st.spinner(f"Processing {f.name}..."):
            doc = fitz.open(stream=f.read(), filetype="pdf")
            raw_text = ""
            for page in doc:
                raw_text += page.get_text()
            doc.close()
            results = extract_fields(raw_text)
        with st.expander(f"Results for {f.name}"):
            st.markdown(f"**Month:** {results['Month']}")
            st.markdown(f"**Units Consumed:** {results['Units Consumed']}")
            st.markdown(f"**Load Sanctioned:** {results['Load Sanctioned']}")
            st.markdown(f"**Contract Demand:** {results['Contract Demand']}")
            st.markdown(f"**Maximum Demand:** {results['Maximum Demand']}")
