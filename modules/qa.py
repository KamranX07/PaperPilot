def answer_question(
    question,
    master_json
):

    question = question.lower()

    if "document" in question:

        docs = master_json.get(
            "documents",
            []
        )

        if not docs:
            return (
                "No documents found."
            )

        return (
            "Required Documents:\n\n• "
            + "\n• ".join(docs)
        )

    if "deadline" in question:

        return (
            "Deadline: "
            + master_json.get(
                "deadline",
                "Not Found"
            )
        )

    if "eligibility" in question:

        return (
            "Eligibility:\n\n"
            + master_json.get(
                "eligibility",
                "Not Found"
            )
        )

    if "form" in question:

        return (
            "Form Name: "
            + master_json.get(
                "form_name",
                "Unknown"
            )
        )

    return (
        "I don't know how to answer that yet."
    )