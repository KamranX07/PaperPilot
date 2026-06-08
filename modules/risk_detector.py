def generate_risks(master_json):

    risks = []

    if master_json.get("deadline") == "Not Found":

        risks.append(
            "⚠ Deadline not found in form."
        )

    if not master_json.get("documents"):

        risks.append(
            "⚠ No required documents detected."
        )

    if len(master_json.get("documents", [])) < 2:

        risks.append(
            "⚠ Very few documents detected. Review manually."
        )

    if master_json.get("eligibility") == "Not Found":

        risks.append(
            "⚠ Eligibility criteria not detected."
        )

    if not master_json.get("contact_info"):

        risks.append(
            "⚠ Contact information missing."
        )

    if not risks:

        risks.append(
            "✅ No major issues detected."
        )

    return "\n\n".join(risks)