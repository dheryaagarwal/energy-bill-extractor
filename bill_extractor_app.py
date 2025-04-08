import streamlit as st
import fitz  # PyMuPDF
import re

###############################################################################
# 1) Bidirectional search helpers
###############################################################################
def search_numeric_around(lines, idx, max_offset=3):
    """
    Look up to 'max_offset' lines above and below 'idx'
    for the first numeric (float or int) in that range.
    Return "" if none found.
    """
    indices_to_check = []
    line_count = len(lines)

    # Lines above
    for up in range(1, max_offset+1):
        if idx - up >= 0:
            indices_to_check.append(idx - up)
    # The label line itself
    indices_to_check.append(idx)
    # Lines below
    for down in range(1, max_offset+1):
        if idx + down < line_count:
            indices_to_check.append(idx + down)

    # Check each candidate line in ascending order of distance
    # We want the closest line that has a valid numeric.
    # We'll sort by the absolute distance from idx, then by up < down priority
    # so that lines just above are checked before lines further below, etc.
    def distance_score(line_idx):
        return abs(line_idx - idx)

    indices_sorted = sorted(indices_to_check, key=distance_score)

    for candidate_i in indices_sorted:
        val = extract_first_numeric(lines[candidate_i])
        if val:
            return val
    return ""

def search_month_around(lines, idx, max_offset=3):
    """
    Look up to 'max_offset' lines above and below 'idx'
    for a pattern like MAR-2025 or May-2024.
    Return "" if none found.
    """
    line_count = len(lines)
    indices_to_check = []

    # Lines above
    for up in range(1, max_offset+1):
        if idx - up >= 0:
            indices_to_check.append(idx - up)
    # The label line itself
    indices_to_check.append(idx)
    # Lines below
    for down in range(1, max_offset+1):
        if idx + down < line_count:
            indices_to_check.append(idx + down)

    # Sort by distance to label line
    def distance_score(line_idx):
        return abs(line_idx - idx)

    indices_sorted = sorted(indices_to_check, key=distance_score)

    for candidate_i in indices_sorted:
        m = re.search(r'\b([A-Za-z]{3,}-\d{4})\b', lines[candidate_i])
        if m:
            return m.group(1)
    return ""

def search_units_consumed_around(lines, idx, max_offset=3):
    """
    Look up to 'max_offset' lines above and below 'idx'
    for a 3-6 digit number (like 4018 or 28261).
    Return "" if none found.
    """
    line_count = len(lines)
    indices_to_check = []

    # Lines above
    for up in range(1, max_offset+1):
        if idx - up >= 0:
            indices_to_check.append(idx - up)
    # The label line itself
    indices_to_check.append(idx)
    # Lines below
    for down in range(1, max_offset+1):
        if idx + down < line_count:
            indices_to_check.append(idx + down)

    def distance_score(line_idx):
        return abs(line_idx - idx)

    indices_sorted = sorted(indices_to_check, key=distance_score)

    for candidate_i in indices_sorted:
        # Remove commas for easier matching
        clean_line = lines[candidate_i].replace(",", "")
        # Look for 3-6 digits
        m = re.search(r'\b(\d{3,6})\b', clean_line)
        if m:
            return m.group(1)
    return ""

def extract_first_numeric(text_line):
    """
    Returns the first numeric (int/float) from a line, ignoring commas,
    or "" if none found.
    """
    cleaned = text_line.replace(",", "")
    match = re.search(r'(\d+(?:\.\d+)?)', cleaned)
    if match:
        return match.group(1)
    return ""

###############################################################################
# 2) The main parse function: line by line, but searching around each label
###############################################################################
def parse_bidirectional(lines, debug=False):
    """
    We iterate over all lines. When we find a label (e.g. 'Load Sanctioned'),
    we call a function that looks up to 3 lines above and below for the numeric.

    The same for 'Units Consumed', 'Month', 'Contract Demand', 'Maximum Demand'.
    """
    results = {
        "Month": None,
        "Units Consumed": None,
        "Load Sanctioned": None,
        "Contract Demand": None,
        "Maximum Demand": None
    }

    for i, line in enumerate(lines):
        lower = line.lower()

        # Month
        if "month" in lower and results["Month"] is None:
            found = search_month_around(lines, i, max_offset=3)
            if found:
                results["Month"] = found

        # Units Consumed
        if "units consumed" in lower and results["Units Consumed"] is None:
            found_units = search_units_consumed_around(lines, i, max_offset=3)
            if found_units:
                results["Units Consumed"] = found_units

        # Load Sanctioned
        if "load sanctioned" in lower and results["Load Sanctioned"] is None:
            found_load = search_numeric_around(lines, i, max_offset=3)
            if found_load:
                results["Load Sanctioned"] = found_load

        # Contract Demand
        if ("contract demand" in lower or "cont. demand" in lower) and results["Contract Demand"] is None:
            found_cd = search_numeric_around(lines, i, max_offset=3)
            if found_cd:
                results["Contract Demand"] = found_cd

        # Maximum Demand
        if any(kw in lower for kw in ["maximum demand", "max demand", "maximum  demand", "net max demand"]) and results["Maximum Demand"] is None:
            found_md = search_numeric_around(lines, i, max_offset=3)
            if found_md:
                results["Maximum Demand"] = found_md

    return results

###############################################################################
# 3) Fallback: text-wide search if something is still missing
###############################################################################
def fallback_search_whole_text(pdf_text):
    """
    If bidirectional line-based logic fails, do a broad search in the entire text.
    """
    cleaned = pdf_text.replace(",", "")
    res = {
        "Month": None,
        "Units Consumed": None,
        "Load Sanctioned": None,
        "Contract Demand": None,
        "Maximum Demand": None
    }

    # Month fallback
    mm = re.search(r'\b([A-Za-z]{3,}-\d{4})\b', cleaned)
    if mm:
        res["Month"] = mm.group(1)

    # Units fallback: look for a 3-6 digit near "units consumed"
    units_m = re.search(r'(\d{3,6})\s+units\s+consumed', cleaned, re.IGNORECASE)
    if units_m:
        res["Units Consumed"] = units_m.group(1)

    # Also try total/net units
    if not res["Units Consumed"]:
        t2 = re.search(r'(?:total units|net units supplied)\s*(\d{3,6})', cleaned, re.IGNORECASE)
        if t2:
            res["Units Consumed"] = t2.group(1)

    # Demand fallback: grab all numbers + KW/KVA
    all_kw = re.findall(r'(\d+(?:\.\d+))\s*(?:KW|KVA)', cleaned, re.IGNORECASE)
    if len(all_kw) >= 1:
        res["Load Sanctioned"] = all_kw[0]
    if len(all_kw) >= 2:
        res["Contract Demand"] = all_kw[1]

    # "Contract Demand" direct
    cd2 = re.search(r'(?:contract demand|cont\. demand)\s*(\d+(?:\.\d+)?)', cleaned, re.IGNORECASE)
    if cd2:
        res["Contract Demand"] = cd2.group(1)

    # "Maximum Demand" direct
    md = re.search(r'(?:max demand|maximum demand|net max demand)\s*(\d+(?:\.\d+)?)', cleaned, re.IGNORECASE)
    if md:
        res["Maximum Demand"] = md.group(1)

    return res

###############################################################################
# 4) Combine approach
###############################################################################
def extract_all_fields(pdf_text, debug=False):
    # 1) Split into lines
    lines = [ln.strip() for ln in pdf_text.splitlines() if ln.strip()]
    if debug:
        st.write("### Debug: Raw Lines")
        for idx, ln in enumerate(lines):
            st.write(f"[{idx}] {ln}")

    # 2) Do the bidirectional line-based parse
    line_based = parse_bidirectional(lines, debug=debug)

    # 3) Fallback if any is None
    fallback = fallback_search_whole_text(pdf_text)

    # Merge
    final = {}
    for f in ["Month", "Units Consumed", "Load Sanctioned", "Contract Demand", "Maximum Demand"]:
        val_line = line_based[f]
        val_fb   = fallback[f]
        chosen = val_line if val_line else val_fb
        if not chosen:
            chosen = "Not Found"

        # Clean up any trailing ".00000"
        if isinstance(chosen, str):
            chosen = chosen.replace(".00000", "")
        final[f] = chosen

    return final

###############################################################################
# 5) Streamlit App
###############################################################################
st.set_page_config(page_title="Bidirectional Bill Extractor", layout="wide")
st.title("Bidirectional Energy Bill PDF Extractor")

st.write("""
**This version looks up to 3 lines above and below each label** to handle
PDFs where numeric values appear either before or after the label.

Target fields:
1. **Month** (e.g., MAR-2025 / May-2024)  
2. **Units Consumed** (e.g., 4018 / 28261)  
3. **Load Sanctioned** (e.g., 35.0)  
4. **Contract Demand** (e.g., 35.0 / 120)  
5. **Maximum Demand** (e.g., 21.94 / 108)
""")

debug_mode = st.sidebar.checkbox("Show Debug Info?", value=False)

uploaded_files = st.file_uploader("Upload your PDF bills", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for f in uploaded_files:
        with st.spinner(f"Processing {f.name}..."):
            doc = fitz.open(stream=f.read(), filetype="pdf")
            raw_text = ""
            for page in doc:
                raw_text += page.get_text()
            doc.close()

            if debug_mode:
                st.write(f"## Raw PDF Text for {f.name}")
                st.text_area("Raw PDF Text", raw_text, height=300)

            final_results = extract_all_fields(raw_text, debug=debug_mode)

        with st.expander(f"Results for {f.name}"):
            st.markdown(f"**Month:** {final_results['Month']}")
            st.markdown(f"**Units Consumed:** {final_results['Units Consumed']}")
            st.markdown(f"**Load Sanctioned:** {final_results['Load Sanctioned']}")
            st.markdown(f"**Contract Demand:** {final_results['Contract Demand']}")
            st.markdown(f"**Maximum Demand:** {final_results['Maximum Demand']}")
