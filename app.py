import gradio as gr

from modules.ocr import extract_text


def analyze_document(file):

    if file is None:
        return "Please upload a file."

    extracted_text = extract_text(file.name)

    return f"""
    Document Processed Successfully

    ----------------------------

    {extracted_text}
    """


with gr.Blocks(title="PaperPilot") as demo:

    gr.Markdown("# PaperPilot")

    file_input = gr.File(
        label="Upload Form"
    )

    output_text = gr.Textbox(
        label="Extracted Text",
        lines=20
    )

    analyze_btn = gr.Button(
        "Analyze Form"
    )

    analyze_btn.click(
        fn=analyze_document,
        inputs=file_input,
        outputs=output_text
    )

demo.launch()