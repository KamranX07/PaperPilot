import re


def extract_deadline(text):

    pattern = r"\b\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}\b"

    matches = re.findall(
        pattern,
        text,
        re.IGNORECASE
    )

    return matches[0] if matches else "Not Found"


def extract_documents(text):

    common_docs = [
        "aadhaar",
        "income certificate",
        "marksheet",
        "passport photo",
        "domicile certificate",
        "caste certificate",
        "bank passbook"
    ]

    found = []

    lower_text = text.lower()

    for doc in common_docs:

        if doc in lower_text:
            found.append(doc.title())

    return found


def extract_form_name(text):

    lines = text.split("\n")

    for line in lines:

        if len(line.strip()) > 5:

            return line.strip()

    return "Unknown Form"


def extract_eligibility(text):

    eligibility_keywords = [
        "eligibility",
        "eligible",
        "income"
    ]

    lines = text.split("\n")

    for line in lines:

        lower = line.lower()

        if any(
            keyword in lower
            for keyword in eligibility_keywords
        ):
            return line.strip()

    return "Not Found"


def build_master_json(text):

    return {
        "form_name": extract_form_name(text),
        "deadline": extract_deadline(text),
        "eligibility": extract_eligibility(text),
        "documents": extract_documents(text),
        "contact_info": ""
    }