import re


def extract_timeline(text):

    timeline = []

    lines = text.split("\n")

    date_pattern = (
        r"\b\d{1,2}\s"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|"
        r"January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s\d{4}\b"
    )

    for i, line in enumerate(lines):

        matches = re.findall(
            date_pattern,
            line,
            re.IGNORECASE
        )

        if matches:

            event = re.sub(
                date_pattern,
                "",
                line,
                flags=re.IGNORECASE
            ).strip(" :-")

            timeline.append([
                matches[0],
                event
            ])

    return timeline