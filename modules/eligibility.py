import re


def extract_income_limit(eligibility_text):

    pattern = r'(\d+(?:\.\d+)?)'

    matches = re.findall(
        pattern,
        eligibility_text
    )

    if not matches:
        return None

    number = float(matches[0])

    if number < 100:
        number *= 100000

    return int(number)


def check_eligibility(
    master_json,
    income
):

    eligibility_text = master_json.get(
        "eligibility",
        ""
    )

    limit = extract_income_limit(
        eligibility_text
    )

    if limit is None:

        return (
            "⚠ Unable to determine eligibility rules."
        )

    if income <= limit:

        return (
            f"✅ Eligible\n\n"
            f"Income Limit: ₹{limit:,}"
        )

    return (
        f"❌ Not Eligible\n\n"
        f"Income Limit: ₹{limit:,}"
    )