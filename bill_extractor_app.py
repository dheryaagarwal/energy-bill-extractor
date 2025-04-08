def extract_fields(text):
    results = {
        "Month": "Not Found",
        "Units Consumed": "Not Found",
        "Sanctioned Load (kW)": "Not Found",
        "Contract Demand (kW)": "Not Found",
        "Maximum Demand (kW)": "Not Found"
    }

    lines = text.split('\n')

    for line in lines:
        lower_line = line.lower()

        if "month" in lower_line and results["Month"] == "Not Found":
            match = re.search(r'month\s*[:\-]?\s*([A-Z]{3}-\d{4})', line, re.IGNORECASE)
            if match:
                results["Month"] = match.group(1).strip()

        if "units consumed" in lower_line and results["Units Consumed"] == "Not Found":
            match = re.search(r'units\s*consumed\s*[:\-]?\s*([\d,]+)', line, re.IGNORECASE)
            if match:
                results["Units Consumed"] = match.group(1).replace(",", "").strip()

        if "load sanctioned" in lower_line and results["Sanctioned Load (kW)"] == "Not Found":
            match = re.search(r'load\s*sanctioned\s*[:\-]?\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                results["Sanctioned Load (kW)"] = match.group(1).strip()

        if "contract demand" in lower_line and results["Contract Demand (kW)"] == "Not Found":
            match = re.search(r'contract\s*demand\s*[:\-]?\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                results["Contract Demand (kW)"] = match.group(1).strip()

        if "maximum demand" in lower_line and results["Maximum Demand (kW)"] == "Not Found":
            match = re.search(r'maximum\s*demand\s*[:\-]?\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                results["Maximum Demand (kW)"] = match.group(1).strip()

    return results
