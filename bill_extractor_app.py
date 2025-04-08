import streamlit as st
import fitz  # PyMuPDF
import re

# -----------------------------------------------------
# 1) HELPERS: line-based searching
# -----------------------------------------------------

def get_first_numeric(line: str) -> str:
    """
    Return the first integer/float in 'line', ignoring commas.
    If none found, return "".
    """
    line = line.replace(",", "")  # remove commas
    match = re.search(r'(\d+(?:\.\d+)?)', line)
    return match.group(1) if match else ""

def next_non_empty_line(lines, i):
    """
    Return the next non-empty line after index i,
    or "" if none is found.
    """
    j = i + 1
    while j < len(lines):
        if lines[j].strip():
            return lines[j]
        j += 1
    return ""

def parse_line_by_line(lines):
    """
    Parse the PDF by scanning lines in order, looking
    for target labels & numeric data on the same or next line.
    Returns a dict with partial or full results.
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

        # Month
        if "month" in lower_line and results["Month"] is None:
            # same line
            match = re.search(r'([A-Za-z]{3,}-\d{4})', line)
            if match:
                results["Month"] = match.group(1)
            else:
                # next line
                nxt = next_non_empty_line(lines, i)
                m2 = re.search(r'([A-Za-z]{3,}-\d{4})', nxt)
                if m2:
                    results["Month"] = m2.group(1)

        # Units Consumed
        # Check if line has "units consumed"
        if "units consumed" in lower_line and results["Units Consumed"] is None:
            # Merge current + next line to handle jammed text
            merged = line + " " + next_non_empty_line(lines, i)
            m_units = re.search(r'(\d[\d\.]*)[^\n]*units\s*consumed', merged, re.IGNORECASE)
            if m_units:
                val = m_units.group(1).replace(".00000", "")
                results["Units Consumed"] = val
            else:
                # fallback numeric on next line
                maybe = get_first_numeric(next_non_empty_line(lines, i))
                if maybe:
                    results["Units Consumed"] = maybe

        # Also check lines with "total units" or "net units supplied"
        if any(k in lower_line for k in ["total units", "net units supplied"]) and results["Units Consumed"] is None:
            # numeric on same or next line
            val = get_first_numeric(line)
            if not val:
                val = get_first_numeric(next_non_empty_line(lines, i))
            if val:
                val = val.replace(".00000", "")
                results["Units Consumed"] = val

        # Load Sanctioned
        if "load sanctioned" in lower_line and results["Load Sanctioned"] is None:
            val = get_first_numeric(line)
            if not val:
                val = get_first_numeric(next_non_empty_line(lines, i))
            if val:
                results["Load Sanctioned"] = val

        # Contract Demand
        if ("contract demand" in lower_line or "cont. demand" in lower_line) and results["Contract Demand"] is None:
            val = get_first_numeric(line)
            if not val:
                val = get_first_numeric(next_non_empty_line(lines, i))
            if val:
                results["Contract Demand"] = val

        # Maximum Demand
        if any(x in lower_line for x in ["maximum demand", "max demand", "net max demand"]) and results["Maximum Demand"] is None:
            val = get_first_numeric(line)
            if not val:
                val = get_first_numeric(next_non_empty_line(lines, i))
            if val:
                results["Maximum Demand"] = val.replace(".00000", "")

    return results

# -----------------------------------------------------
# 2) HELPERS: text-wide fallback searching
# -----------------------------------------------------

def fallback_in_whole_text(text):
    """
    As a fallback, we do broad regex searches on the entire text
    to find any missed fields. We'll anchor around known words
    or patterns, capturing a numeric near them.
    """
    # Clean up text for easier searching
    t = text.replace(",", "")  

    # Prepare a dictionary for fallback
    fallback_results = {
        "Month": None,
        "Units Consumed": None,
        "Load Sanctioned": None,
        "Contract Demand": None,
        "Maximum Demand": None,
    }

    # Month fallback: look for "Month" or direct pattern like "May-2024"
    # We also exclude short patterns like 19-Apr-2025 (common for dates).
    # But let's do a direct approach: "([A-Za-z]{3,}-\d{4})" anywhere in text.
    m_month = re.search(r'([A-Za-z]{3,}-\d{4})', t)
    if m_month:
        fallback_results["Month"] = m_month.group(1)

    # Units consumed fallback: look for "units consumed" plus a numeric near it
    # For example: r"(\d[\d\.]+)\s*units\s*consumed" or the reverse
    m_units = re.search(r'(\d[\d\.]+)\s*(?:units\s*consumed)', t, re.IGNORECASE)
    if m_units:
        fallback_results["Units Consumed"] = m_units.group(1).replace(".00000", "")

    # total/net units
    if not fallback_results["Units Consumed"]:
        m_u2 = re.search(r'(?:total units|net units supplied)\s*(\d[\d\.]+)', t, re.IGNORECASE)
        if m_u2:
            fallback_results["Units Consumed"] = m_u2.group(1).replace(".00000", "")

    # Load Sanctioned fallback
    m_ls = re.search(r'load\s*sanctioned\s*(\d+(?:\.\d+)?)', t, re.IGNORECASE)
    if m_ls:
        fallback_results["Load Sanctioned"] = m_ls.group(1)

    # Contract Demand fallback
    m_cd = re.search(r'(?:contract demand|cont\. demand)\s*(\d+(?:\.\d+)?)', t, re.IGNORECASE)
    if m_cd:
        fallback_results["Contract Demand"] = m_cd.group(1)

    # Maximum Demand fallback
    m_md = re.search(r'(?:maximum demand|max demand|net max demand)\s*(\d+(?:\.\d+)?)', t, re.IGNORECASE)
    if m_md:
        fallback_results["Maximum Demand"] = m_md.group(1).replace(".00000", "")

    return fallback_results

# -----------------------------------------------------
# 3) Main Extraction: Combine both approaches
# -----------------------------------------------------
def extract_fields(pdf_text):
    lines = [ln.strip() for ln in pdf_text.splitlines() if ln.strip()]

    # 1) line-by-line approach
    line_results = parse_line_by_line(lines)

    # 2) text-wide fallback approach
    fallback_results = fallback_in_whole_text(pdf_text)

    # Combine them: if line_results found nothing for a field,
    # use fallback_results. If fallback also has none, remain "Not Found".
    final = {}
    for field in ["Month", "Units Consumed", "Load Sanctioned", "Contract Demand", "Maximum Demand"]:
        val_line = line_results[field]
        val_fb   = fallback_results[field]
        if val_line is not None:
            final[field] = val_line
        elif val_fb is not None:
            final[field] = val_fb
        else:
            final[field] = "Not Found"

        # Convert None -> "Not Found"
        if final[field] is None:
            final[field] = "Not Found"

        # Remove .00000 if it remains
        if isinstance(final[field], str):
            final[field] = final[field].replace(".00000", "")

    return final

# -----------------------------------------------------
# 4) STREAMLIT APP
# -----------------------------------------------------
st.set_page_config(page_title="Universal Bill Extractor", layout="centered")
st.title("Universal Energy Bill PDF Extractor")

st.write("""
**Combines line-by-line parsing + text-wide fallback** to handle multiple PDF layouts.
Target fields:

1. **Month** (e.g., MAR-2025 / May-2024)  
2. **Units Consumed** (e.g., 4018 / 28261)  
3. **Load Sanctioned** (e.g., 35.0)  
4. **Contract Demand** (e.g., 35.0 / 120)  
5. **Maximum Demand** (e.g., 21.94 / 108)  

Upload both your original (`N3372042572.pdf`) and new HT (`1744108547035billDetails.pdf`) bills to test.
""")

uploaded_files = st.file_uploader("Upload PDF(s)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for f in uploaded_files:
        with st.spinner(f"Processing {f.name}..."):
            # Extract all text from PDF
            doc = fitz.open(stream=f.read(), filetype="pdf")
            raw_text = ""
            for page in doc:
                raw_text += page.get_text()
            doc.close()

            # Parse fields
            results = extract_fields(raw_text)

        with st.expander(f"Results for {f.name}"):
            st.markdown(f"- **Month**: {results['Month']}")
            st.markdown(f"- **Units Consumed**: {results['Units Consumed']}")
            st.markdown(f"- **Load Sanctioned**: {results['Load Sanctioned']}")
            st.markdown(f"- **Contract Demand**: {results['Contract Demand']}")
            st.markdown(f"- **Maximum Demand**: {results['Maximum Demand']}")
