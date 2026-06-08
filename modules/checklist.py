def generate_checklist(master_json):
    documents = master_json.get(
        "documents",
        []
    )

    checklist = []

    for doc in documents:
        checklist.append({
            doc,
            "Missing"
        })

    return checklist