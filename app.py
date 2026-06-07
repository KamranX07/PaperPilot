import gradio as gr

from modules.ocr import extract_text
from modules.extractor import build_master_json


def analyze_document(file):

    if file is None:
        return "Please upload a file."

    extracted_text = extract_text(file.name)

    master_json = build_master_json(extracted_text)

    return master_json


with gr.Blocks(title="PaperPilot") as demo:

    gr.Markdown("# PaperPilot")

    file_input = gr.File(
        label="Upload Form"
    )

    output_json = gr.JSON(
    label="Form Analysis"
    )

    analyze_btn = gr.Button(
        "Analyze Form"
    )

    analyze_btn.click(
        fn=analyze_document,
        inputs=file_input,
        outputs=output_json
    )

demo.launch()