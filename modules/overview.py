def generate_overview(master_json):

    form_name = master_json.get(
        "form_name",
        "Unknown"
    )

    deadline = master_json.get(
        "deadline",
        "Not Found"
    )

    eligibility = master_json.get(
        "eligibility",
        "Not Found"
    )

    documents = master_json.get(
        "documents",
        []
    )

    docs_text = ""

    for doc in documents:
        docs_text += f"• {doc}\n"

    overview = f"""
# 📄 Form Overview

## Form Name
{form_name}

## 📅 Deadline
{deadline}

## 🎯 Eligibility
{eligibility}

## 📑 Required Documents
{docs_text}
"""

    return overview