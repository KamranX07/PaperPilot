import gradio as gr
from modules.ocr import extract_text
from modules.extractor import build_master_json
from modules.overview import generate_overview
from modules.checklist import generate_checklist

def analyze_document(file):

    if file is None:
        return {}, "Please upload a file.", {}

    extracted_text = extract_text(file.name)
    master_json = build_master_json(extracted_text)
    overview = generate_overview(master_json)
    checklist = generate_checklist(master_json)
    return (
        master_json, 
        overview,
        checklist, 
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

    analyze_btn.click(
        fn=analyze_document,
        inputs=file_input,
        outputs=[
            output_json,
            overview_output,
            checklist_output,
            master_json_state
        ]
    )

demo.launch()