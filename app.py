import gradio as gr
from modules.ocr import extract_text
from modules.extractor import build_master_json
from modules.overview import generate_overview
from modules.checklist import generate_checklist
from modules.eligibility import (check_eligibility)
from modules.timeline import extract_timeline
from modules.risk_detector import (generate_risks)
from modules.verifier import (verify_documents, verification_summary)
from modules.qa import (answer_question)

def analyze_document(file):

    if file is None:
        return {}, "Please upload a file.", {}

    extracted_text = extract_text(file.name)
    master_json = build_master_json(extracted_text)
    overview = generate_overview(master_json)
    checklist = generate_checklist(master_json)
    timeline = extract_timeline(extracted_text)
    risks = generate_risks(master_json)
    return (
        master_json, 
        overview,
        checklist,
        timeline,
        risks, 
        master_json
    )

def run_eligibility_check(
    income,
    master_json
):

    if not master_json:

        return (
            "Please analyze a form first."
        )

    return check_eligibility(
        master_json,
        income
    )

def run_verification(
    files,
    master_json
):

    if not master_json:
        return [], ""

    results = verify_documents(
        files,
        master_json
    )

    summary = verification_summary(
        results
    )

    return results, summary

def run_qa(
    question,
    master_json
):

    if not master_json:

        return (
            "Please analyze a form first."
        )

    return answer_question(
        question,
        master_json
    )

with gr.Blocks(title="PaperPilot") as demo:

    gr.Markdown("# PaperPilot")

    master_json_state = gr.State()

    with gr.Tabs():

        with gr.Tab("Upload & Analyze"):

            file_input = gr.File(
                label="Upload Form"
            )

            analyze_btn = gr.Button(
                "Analyze Form"
            )

            output_json = gr.JSON(
            label="Form Analysis"
            )

        with gr.Tab("Overview"):
            overview_output = gr.Markdown()

        with gr.Tab("Checklist"):
            checklist_output = gr.DataFrame(
                headers=["Documents", "Status"],
                label="Document Checklist"
            )

        with gr.Tab("Eligibility"):

            income_input = gr.Number(
                label="Annual Family Income (₹)"
            )

            check_btn = gr.Button(
                "Check Eligibility"
            )

            eligibility_output = gr.Markdown()

        with gr.Tab("Timeline"):
            timeline_output = gr.DataFrame(
                headers=["Date", "Event"],
                label="Important Dates"
            )

        with gr.Tab("Risk Alerts"):
            risk_output = gr.Markdown()

        with gr.Tab("Document Verification"):
            verify_upload = gr.File(
                file_count="multiple",
                label="Upload Supporting Documents"
            )

            verify_btn = gr.Button(
                "Verify Documents"
            )

            verification_output = gr.DataFrame(
                headers=["Document", "Status"],
                label="Verification Results"
            )

            verification_summary_output = gr.Markdown()

        with gr.Tab("Ask PaperPilot"):

            question_input = gr.Textbox(
                label="Ask a Question"
            )

            ask_btn = gr.Button(
                "Ask"
            )

            answer_output = gr.Markdown()

    analyze_btn.click(
        fn=analyze_document,
        inputs=file_input,
        outputs=[
            output_json,
            overview_output,
            checklist_output,
            timeline_output,
            risk_output,
            master_json_state
        ]
    )

    check_btn.click(
        fn=run_eligibility_check,
        inputs=[
            income_input,
            master_json_state
        ],
        outputs=eligibility_output
        )

    verify_btn.click(
        fn=run_verification,
        inputs=[
            verify_upload,
            master_json_state
        ],
        outputs=[
            verification_output,
            verification_summary_output
        ]
    )

    ask_btn.click(
        fn=run_qa,
        inputs=[
            question_input,
            master_json_state
        ],
        outputs=answer_output
    )

demo.launch()