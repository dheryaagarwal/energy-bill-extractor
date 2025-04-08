import streamlit as st
import fitz  # PyMuPDF
import re

# -----------------------------------------------------
# A. HELPER FUNCTIONS
# -----------------------------------------------------

def next_nonempty_line(lines, idx):
    """Return the next non-empty line after idx, or empty string if none."""
    j = idx + 1
    while j < len(lines):
        if lines[j].strip():
            return lines[j]
        j += 1
    return ""

def get_first_numeric(line: str) -> str:
    """
    Extract the first numeric (int or float) from a line.
    Strips commas, handles decimals.
    """
    clean = line.replace(",", "")
    match = re.search(r'(\d+(\.\d+)?)', clean)
    return match.group(1) if match else ""

def parse_line_by_line(lines):
    """
    1st approach: Loop line by line, look for key words.
    If we find them, parse the same line or next line for a numeric value or a pattern.
    """
    results = {
        "Month": None,
        "Units Consumed": None,
        "Load Sanctioned": None,
        "Contract Demand": None,
        "Maximum Demand": None
    }

    for i, line in enumerate(lines):
        l_lower = line.lower()

        # 1) Month
        if "month" in l_lower and results["Month"] is None:
            # Try something like MAR-2025 or May-2024
            m = re.search(r'([A-Za-z]{3,}-\d{4})', line)
            if m:
                results["Month"] = m.group(1)
            else:
                # Check next line
                nxt = next_nonempty_line(lines, i)
                m2 = re.search(r'([A-Za-z]{3,}-\d{4})', nxt)
                if m2:
                    results["Month"] = m2.group(1)

        # 2) Units Consumed
        if "units consumed" in l_lower and results["Units Consumed"] is None:
            # Possibly jammed with date. Combine current + next line
            combined = line + " " + next_nonempty_line(lines, i)
            # Look for a block of 3-6 digits (e.g. 4018, 28261)
            match_u = re.search(r'\b(\d{3,6})\b', combined.replace(",", ""))
            if match_u:
                results["Units Consumed"] = match_u.group(1)

        # Additional fallback: lines with "total units" or "net units supplied"
        if any(k in l_lower for k in ["total units", "net units supplied"]):
            if results["Units Consumed"] is None:
                # same line or next line
                val = re.search(r'\b(\d{3,6})\b', line.replace(",", ""))
                if not val:
                    nxt = next_nonempty_line(lines, i)
                    val = re.search(r'\b(\d{3,6})\b', nxt.replace(",", ""))
                if val:
                    results["Units Consumed"] = val.group(1)

        # 3) Load Sanctioned
        if "load sanctioned" in l_lower and results["Load Sanctioned"] is None:
            val = get_first_numeric(line)
            if not val:
                val = get_first_numeric(next_nonempty_line(lines, i))
            if val:
                results["Load Sanctioned"] = val

        # 4) Contract Demand (or "Cont. Demand")
        if ("contract demand" in l_lower or "cont. demand" in l_lower) and results["Contract Demand"] is None:
            val = get_first_numeric(line)
            if not val:
                val = get_first_numeric(next_nonempty_line(lines, i))
            if val:
                results["Contract Demand"] = val

        # 5) Maximum Demand (also "max demand" / "net max demand")
        if any(x in l_lower for x in ["maximum demand", "max demand", "net max demand"]) and results["Maximum Demand"] is None:
            val = get_first_numeric(line)
            if not val:
                val = get_first_numeric(next_nonempty_line(lines, i))
            if val:
                results["Maximum Demand"] = val

    return results

def fallback_search_in_text(text):
    """
    2nd approach: Search entire text (broad regex) if line-by-line missed something.
    """
    # Remove commas for easier matching
    txt_clean = text.replace(",", "")

    results = {
        "Month": None,
        "Units Consumed": None,
        "Load Sanctioned": None,
        "Contract Demand": None,
        "Maximum Demand": None
    }

    # 1) Month (e.g. MAR-2025 or May-2024)
    m_month = re.search(r'([A-Za-z]{3,}-\d{4})', txt_clean)
    if m_month:
        results["Month"] = m_month.group(1)

    # 2) Units Consumed (look for 3-6 digit near "units consumed" or "total units"/"net units supplied")
    m_units = re.search(r'(\d{3,6})\s*units\s*consumed', txt_clean, re.IGNORECASE)
    if not m_units:
        m_units = re.search(r'(?:total units|net units supplied)\s*(\d{3,6})', txt_clean, re.IGNORECASE)
    if m_units:
        results["Units Consumed"] = m_units.group(1)

    # 3) Load & Contract Demand: numbers followed by KW or KVA
    # We'll gather them all then guess first is load, second is contract
    all_kw = re.findall(r'(\d+(?:\.\d+)?)\s*(?:KW|KVA)', txt_clean, re.IGNORECASE)
    if all_kw:
        if len(all_kw) >= 1:
            results["Load Sanctioned"] = all_kw[0]
        if len(all_kw) >= 2:
            results["Contract Demand"] = all_kw[1]

    # Also do a direct search for "contract demand" or "cont. demand" + number
    m_cd = re.search(r'(?:contract demand|cont\. demand)\s*(\d+(?:\.\d+)?)', txt_clean, re.IGNORECASE)
    if m_cd:
        results["Contract Demand"] = m_cd.group(1)

    # 4) Maximum Demand
    # Could do a direct search for line like "maximum demand 21.94"
    # or "net max demand 108"
    m_md = re.search(r'(?:maximum demand|max demand|net max demand)\s*(\d+(?:\.\d+)?)', txt_clean, re.IGNORECASE)
    if m_md:
        results["Maximum Demand"] = m_md.group(1)

    return results

def combine_results(line_res, fallback_res):
    """
    Return final. If line-based result is missing, use fallback.
    If both missing, "Not Found".
    """
    final = {}
    fields = ["Month", "Units Consumed", "Load Sanctioned", "Contract Demand", "Maximum Demand"]
    for f in fields:
        # if line-based has a non-None value, keep it
        if line_res[f] is not None:
            val = line_res[f]
        elif fallback_res[f] is not None:
            val = fallback_res[f]
        else:
            val = "Not Found"

        # Remove trailing .00000 if any
        if isinstance(val, str):
            val = val.replace(".00000", "")
        final[f] = val
    return final

def extract_fields(pdf_text: str, debug=False):
    """
    1) Split text into lines -> parse line by line
    2) Fallback: broad regex across entire text
    3) Combine results
    """
    lines = [ln.strip() for ln in pdf_text.splitlines() if ln.strip()]
    
    if debug:
        st.subheader("Debug: Raw Lines")
        for i, ln in enumerate(lines):
            st.write(f"[{i}] {ln}")

    line_res = parse_line_by_line(lines)
    fallback_res = fallback_search_in_text(pdf_text)
    final_res = combine_results(line_res, fallback_res)
    return final_res

# -----------------------------------------------------
# B. STREAMLIT APP
# -----------------------------------------------------
st.set_page_config(page_title="Final Bill Extractor", layout="centered")
st.title("💡 Final Energy Bill PDF Extractor with Debug Toggle")

# Debug toggle in sidebar
debug_mode = st.sidebar.checkbox("Show debug info (raw text & lines)?", value=False)

st.write("""
Upload your PDF bills (e.g. **N3372042572.pdf** or **1744108547035billDetails.pdf**) to extract:
1. **Month**  
2. **Units Consumed**  
3. **Load Sanctioned**  
4. **Contract Demand**  
5. **Maximum Demand**  
""")

uploaded_files = st.file_uploader("Upload PDF(s)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for f in uploaded_files:
        with st.spinner(f"Processing {f.name}..."):
            doc = fitz.open(stream=f.read(), filetype="pdf")
            pdf_text = ""
            for page in doc:
                pdf_text += page.get_text()
            doc.close()

            # If debug_mode, show the entire text for inspection
            if debug_mode:
                st.subheader(f"Raw PDF Text for {f.name}")
                st.text_area("Raw PDF Text", pdf_text, height=300)

            results = extract_fields(pdf_text, debug=debug_mode)

        with st.expander(f"Results for {f.name}"):
            st.markdown(f"- **Month:** {results['Month']}")
            st.markdown(f"- **Units Consumed:** {results['Units Consumed']}")
            st.markdown(f"- **Load Sanctioned:** {results['Load Sanctioned']}")
            st.markdown(f"- **Contract Demand:** {results['Contract Demand']}")
            st.markdown(f"- **Maximum Demand:** {results['Maximum Demand']}")
