import os


def verify_documents(
    uploaded_files,
    master_json
):

    required_docs = master_json.get(
        "documents",
        []
    )

    uploaded_names = []

    if uploaded_files:

        for file in uploaded_files:

            filename = os.path.basename(
                file.name
            ).lower()

            uploaded_names.append(
                filename
            )

    results = []

    for doc in required_docs:

        doc_lower = doc.lower()

        found = False

        for filename in uploaded_names:

            words = doc_lower.split()

            if any(
                word in filename
                for word in words
            ):
                found = True
                break

        status = (
            "✅ Uploaded"
            if found
            else "❌ Missing"
        )

        results.append([
            doc,
            status
        ])

    return results

def verification_summary(results):

    uploaded = sum(
        1
        for row in results
        if "Uploaded" in row[1]
    )

    total = len(results)

    return (
        f"Documents Submitted: "
        f"{uploaded}/{total}"
    )