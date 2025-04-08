import streamlit as st
import fitz  # PyMuPDF
import re

def get_first_numeric(line: str) -> str:
    """
    Return the first numeric (int or float) found in the given line,
    ignoring commas. If none found, return "".
    """
    line = line.replace(",", "")  # remove commas
    match = re.search(r'(\d+(?:\.\d+)?)', line)
    if match:
        return match.group(1)
    return ""

def parse_bill(lines):
    """
    Parse out the 5 fields from the PDF lines:
      1) Month
      2) Units Consumed
      3) Load Sanctioned
      4) Contract Demand
      5) Maximum Demand
    """

    # Initialize everything to "Not Found"
    results = {
        "Month": "Not Found",
        "Units Consumed": "Not Found",
        "Load Sanctioned": "Not Found",
        "Contract Demand": "Not Found",
        "Maximum Demand": "Not Found"
    }

    # Helper function: get line[i+1] if exists, else ""
    def next_line(i):
        return lines[i+1] if (i+1 < len(lines)) else ""

    # We’ll do a pass through lines. This is manual but robust.
    for i, line in enumerate(lines):
        lower_line = line.lower()

        # --------------------------
        # 1) Load Sanctioned
        # --------------------------
        if "load sanctioned" in lower_line and results["Load Sanctioned"] == "Not Found":
            # The numeric is often on the next line
            # or possibly on the same line
            maybe = get_first_numeric(line)
            if not maybe:
                maybe = get_first_numeric(next_line(i))
            if maybe:
                results["Load Sanctioned"] = maybe

        # --------------------------
        # 2) Contract Demand (or "Cont. Demand")
        # --------------------------
        if ("contract demand" in lower_line or "cont. demand" in lower_line) and results["Contract Demand"] == "Not Found":
            maybe = get_first_numeric(line)
            if not maybe:
                maybe = get_first_numeric(next_line(i))
            if maybe:
                results["Contract Demand"] = maybe

        # --------------------------
        # 3) Maximum Demand
        #    (Could be "Maximum Demand", "Max Demand", "Net Max Demand")
        # --------------------------
        if any(x in lower_line for x in ["maximum demand", "max demand", "net max demand"]) and results["Maximum Demand"] == "Not Found":
            maybe = get_first_numeric(line)
            if not maybe:
                maybe = get_first_numeric(next_line(i))
            if maybe:
                # Remove .00000 if it appears
                results["Maximum Demand"] = maybe.replace(".00000", "")

        # --------------------------
        # 4) Month
        #    We look for lines containing "Month" or a string like "MAR-2025Month..."
        # --------------------------
        if "month" in lower_line and results["Month"] == "Not Found":
            # Attempt to directly find something like "MAR-2025" on this line
            m = re.search(r'([A-Za-z]{3,}-\d{4})', line)
            if m:
                results["Month"] = m.group(1)
            else:
                # check next line if the month is there
                nl = next_line(i)
                m2 = re.search(r'([A-Za-z]{3,}-\d{4})', nl)
                if m2:
                    results["Month"] = m2.group(1)

        # --------------------------
        # 5) Units Consumed
        #    We often see "Units consumed" on line i, and the actual number stuck together
        #    or on the next line. 
        # --------------------------
        if "units consumed" in lower_line and results["Units Consumed"] == "Not Found":
            # Try same line first
            # e.g., "4,01803-Apr-2025 Units consumedBill Date"
            # Merge it with the next line just in case the numeric got split
            merged = line + " " + next_line(i)
            numeric = get_first_numeric(merged)
            if numeric:
                # remove trailing .00000 if any
                results["Units Consumed"] = numeric.replace(".00000", "")
        
        # Additional fallback: 
        # If not found yet, check if line has "Total Units" or "Net Units Supplied"
        if ("total units" in lower_line or "net units supplied" in lower_line) and results["Units Consumed"] == "Not Found":
            # numeric might be on same line or next line
            maybe = get_first_numeric(line)
            if not maybe:
                maybe = get_first_numeric(next_line(i))
            if maybe:
                results["Units Consumed"] = maybe.replace(".00000", "")

    return results

# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(page_title="Line-by-Line Bill Extractor", layout="centered")
st.title("Line-by-Line Energy Bill PDF Extractor")

st.write("""
This approach:

- Reads each PDF line,
- Looks for exact labels (e.g. "Load Sanctioned") and parses the next line for the numeric value.
- Merges lines for tricky "units consumed" text.

**Try both of your PDFs:**  
- `N3372042572.pdf` (we expect MAR-2025, 4018, 35.0, 35.0, 21.94)  
- `1744108547035billDetails.pdf` (we expect May-2024, 28261, [maybe no Load Sanctioned], 120, 108).  
""")

uploaded_files = st.file_uploader("Upload PDF bills", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for f in uploaded_files:
        with st.spinner(f"Processing {f.name}..."):
            doc = fitz.open(stream=f.read(), filetype="pdf")
            raw_text = ""
            for page in doc:
                raw_text += page.get_text()
            doc.close()

            # Split into stripped, non-empty lines
            lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

            results = parse_bill(lines)

        with st.expander(f"Results for {f.name}"):
            st.markdown(f"**Month:** {results['Month']}")
            st.markdown(f"**Units Consumed:** {results['Units Consumed']}")
            st.markdown(f"**Load Sanctioned:** {results['Load Sanctioned']}")
            st.markdown(f"**Contract Demand:** {results['Contract Demand']}")
            st.markdown(f"**Maximum Demand:** {results['Maximum Demand']}")
