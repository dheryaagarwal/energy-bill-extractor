import streamlit as st
import fitz  # PyMuPDF
import re

def extract_fields(pdf_text):
    """
    Extract these fields from a PDF's text:
      1) Month
      2) Units Consumed
      3) Load Sanctioned
      4) Contract Demand
      5) Maximum Demand
    """

    # Split text into a list of stripped, non-empty lines
    raw_lines = [ln.strip() for ln in pdf_text.splitlines() if ln.strip()]

    # -------------------------------------------------
    # OPTIONAL: Uncomment for debugging the raw lines:
    # -------------------------------------------------
    # st.write("DEBUG: Raw lines from PDF:")
    # for i, ln in enumerate(raw_lines):
    #     st.write(f"[{i}] {ln}")
    # st.write("-----")

    # Prepare dictionary with default "Not Found" values
    fields = {
        "Month": "Not Found",
        "Units Consumed": "Not Found",
        "Load Sanctioned": "Not Found",
        "Contract Demand": "Not Found",
        "Maximum Demand": "Not Found",
    }

    # Helper: get line or the next non-empty line
    def get_line_or_next(i):
        """
        Return the content of line i if it exists;
        otherwise check subsequent lines until a non-empty one is found;
        if none found, return "".
        """
        if i < len(raw_lines):
            # current line
            line = raw_lines[i]
            if line.strip():
                return line
        # else go forward
        j = i + 1
        while j < len(raw_lines):
            if raw_lines[j].strip():
                return raw_lines[j]
            j += 1
        return ""

    # Let's loop line-by-line and check for keywords
    for i, line in enumerate(raw_lines):
        lower_line = line.lower()

        # -----------------------
        # 1) Month
        # -----------------------
        # If "month" is on this line, let's parse a pattern like MAR-2025 or May-2024
        if "month" in lower_line and fields["Month"] == "Not Found":
            # Try same line first
            match = re.search(r'([A-Za-z]{3,}-\d{4})', line)
            if match:
                fields["Month"] = match.group(1)
            else:
                # fallback: look on the next line
                next_line = get_line_or_next(i + 1)
                match2 = re.search(r'([A-Za-z]{3,}-\d{4})', next_line)
                if match2:
                    fields["Month"] = match2.group(1)

        # -----------------------
        # 2) Units Consumed
        # -----------------------
        # If "units consumed" is on this line
        if "units consumed" in lower_line and fields["Units Consumed"] == "Not Found":
            # Try same line for a number (commas allowed)
            match = re.search(r'(\d[\d,\.]*)[^\n]*units\s*consumed', line, re.IGNORECASE)
            if match:
                fields["Units Consumed"] = match.group(1).replace(",", "").replace(".00000", "")
            else:
                # fallback: look for a numeric pattern on the next line
                next_line = get_line_or_next(i + 1)
                match2 = re.search(r'(\d[\d,\.]*)', next_line)
                if match2:
                    fields["Units Consumed"] = match2.group(1).replace(",", "").replace(".00000", "")

        # Another check for "total units" or "net units supplied"
        # (in case "units consumed" wasn't found in the new PDF)
        if any(kw in lower_line for kw in ["total units", "net units supplied"]) and fields["Units Consumed"] == "Not Found":
            # e.g., "Total Units 28261.00000"
            match = re.search(r'(\d[\d,\.]+)', line)
            if match:
                fields["Units Consumed"] = match.group(1).replace(",", "").replace(".00000", "")

        # -----------------------
        # 3) Load Sanctioned
        # -----------------------
        # If "load sanctioned" on this line
        if "load sanctioned" in lower_line and fields["Load Sanctioned"] == "Not Found":
            # Look for number in same or next line
            match = re.search(r'(\d+(?:\.\d+)?)[^\n]*(kw|kva)?', line, re.IGNORECASE)
            if match:
                fields["Load Sanctioned"] = match.group(1)
            else:
                # fallback: next line
                next_line = get_line_or_next(i + 1)
                match2 = re.search(r'(\d+(?:\.\d+)?)[^\n]*(kw|kva)?', next_line, re.IGNORECASE)
                if match2:
                    fields["Load Sanctioned"] = match2.group(1)

        # -----------------------
        # 4) Contract Demand
        # -----------------------
        # If "contract demand" or "cont. demand" on this line
        if ("contract demand" in lower_line or "cont. demand" in lower_line) and fields["Contract Demand"] == "Not Found":
            match = re.search(r'(\d+(?:\.\d+)?)[^\n]*(kw|kva)?', line, re.IGNORECASE)
            if match:
                fields["Contract Demand"] = match.group(1)
            else:
                # fallback: next line
                next_line = get_line_or_next(i + 1)
                match2 = re.search(r'(\d+(?:\.\d+)?)[^\n]*(kw|kva)?', next_line, re.IGNORECASE)
                if match2:
                    fields["Contract Demand"] = match2.group(1)

        # -----------------------
        # 5) Maximum Demand
        # -----------------------
        # If "maximum demand", "max demand", or "net max demand" on this line
        if any(kw in lower_line for kw in ["maximum demand", "max demand", "net max demand"]) and fields["Maximum Demand"] == "Not Found":
            # look for numeric on same line
            match = re.search(r'(\d+(?:\.\d+))', line)
            if match:
                fields["Maximum Demand"] = match.group(1).replace(".00000", "")
            else:
                # fallback: next line
                next_line = get_line_or_next(i + 1)
                match2 = re.search(r'(\d+(?:\.\d+))', next_line)
                if match2:
                    fields["Maximum Demand"] = match2.group(1).replace(".00000", "")

    return fields

# -----------------------------------------------------------------
# Streamlit App
# -----------------------------------------------------------------
st.set_page_config(page_title="Energy Bill Extractor", layout="centered")
st.title("Robust Energy Bill PDF Extractor")

st.write("""
Upload one or more electricity bill PDFs to extract:
1. **Month**  
2. **Units Consumed**  
3. **Load Sanctioned**  
4. **Contract Demand**  
5. **Maximum Demand**  

This version does:
- **Line-by-line** scanning
- **Same-line or next-line** searches for each field
- More flexible regex to handle merged text (e.g. "4,01803-Apr-2025Units consumed")
- Works better across both old & new HT format PDFs
""")

uploaded_files = st.file_uploader("Upload your PDF bills", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for file in uploaded_files:
        with st.spinner(f"Processing {file.name}..."):
            doc = fitz.open(stream=file.read(), filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            results = extract_fields(text)

        with st.expander(f"Results for {file.name}"):
            st.markdown(f"**Month**: {results['Month']}")
            st.markdown(f"**Units Consumed**: {results['Units Consumed']}")
            st.markdown(f"**Load Sanctioned**: {results['Load Sanctioned']}")
            st.markdown(f"**Contract Demand**: {results['Contract Demand']}")
            st.markdown(f"**Maximum Demand**: {results['Maximum Demand']}")
