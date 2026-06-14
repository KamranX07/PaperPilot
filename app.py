import os
import json
import time
from hashlib import sha256
from typing import Any, Dict, List, Tuple

import gradio as gr

from modules.ocr import extract_text
from modules.llm_provider import extract_form_data, ask_llm
from modules.overview import generate_overview
from modules.checklist import generate_checklist
from modules.eligibility import check_eligibility
from modules.timeline import extract_timeline
from modules.risk_detector import generate_risks
from modules.verifier import verify_documents, verification_summary


def _read_css() -> str:
    css_content = ""
    css_path = os.path.join("assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
    return css_content


def _file_fingerprint(file_obj) -> str:
    """Lightweight key for caching: file name + size + mtime if available."""
    if file_obj is None:
        return ""
    name = getattr(file_obj, "name", "") or ""
    size = getattr(file_obj, "size", None)
    mtime = getattr(file_obj, "last_modified", None)
    raw = f"{name}|{size}|{mtime}".encode("utf-8", errors="ignore")
    return sha256(raw).hexdigest()


# In-memory cache (server-side)
_CACHE: Dict[str, Dict[str, Any]] = {}


def analyze_document(file):
    """Analyze uploaded form and return all outputs for the dashboard."""
    if file is None:
        return (
            {},
            gr.update(value="ℹ Upload a form first.", visible=True),
            gr.update(visible=False),
            gr.update(value="ℹ Analyze a form to see results.", visible=True),
            gr.update(visible=False),
            gr.update(value="ℹ No timeline information found in this form.", visible=True),
            gr.update(visible=False),
            "ℹ No risks detected.",
            gr.update(value="ℹ Upload supporting documents to verify.", visible=True),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            gr.update(value="ℹ Ready", visible=False),
            gr.update(value=[], visible=False),
        )

    key = _file_fingerprint(file)
    cached = _CACHE.get(key)

    if cached:
        master_json = cached["master_json"]
        overview = cached["overview"]
        checklist = cached["checklist"]
        timeline = cached["timeline"]
        risks = cached["risks"]
        status = f"✅ Loaded from cache ({time.strftime('%H:%M:%S')})"
    else:
        extracted_text = extract_text(file.name)
        master_json = extract_form_data(extracted_text)
        overview = generate_overview(master_json)
        checklist = generate_checklist(master_json)
        timeline = extract_timeline(extracted_text)
        risks = generate_risks(master_json)
        status = f"✅ Analysis complete ({time.strftime('%H:%M:%S')})"
        _CACHE[key] = {
            "master_json": master_json,
            "overview": overview,
            "checklist": checklist,
            "timeline": timeline,
            "risks": risks,
        }

    # Checklist empty state
    if not checklist:
        checklist_empty_update = gr.update(value="ℹ Analyze a form to see results.", visible=True)
        checklist_output_update = gr.update(visible=False)
    else:
        checklist_empty_update = gr.update(visible=False)
        checklist_output_update = gr.update(value=checklist, visible=True)

    # Timeline empty state
    if not timeline:
        timeline_empty_update = gr.update(value="ℹ No timeline information found in this form.", visible=True)
        timeline_output_update = gr.update(visible=False)
    else:
        timeline_empty_update = gr.update(visible=False)
        timeline_output_update = gr.update(value=timeline, visible=True)

    # Risks display
    if not risks or (isinstance(risks, str) and risks.strip() == "✅ No major issues detected."):
        risks_display = "ℹ No risks detected."
    else:
        risks_display = risks

    # Reset verification outputs when a new form is analyzed
    verification_empty_update = gr.update(value="ℹ Upload supporting documents to verify.", visible=True)
    verification_output_update = gr.update(visible=False)
    verification_summary_update = gr.update(value="", visible=False)

    # Overview empty state
    if not overview:
        overview_empty_update = gr.update(value="ℹ Upload a form first.", visible=True)
        overview_output_update = gr.update(visible=False)
    else:
        overview_empty_update = gr.update(value="", visible=False)
        overview_output_update = gr.update(value=overview, visible=True)

    completeness = 0
    if master_json:
        completeness += 25
    if checklist:
        completeness += 25
    if timeline:
        completeness += 25
    if risks_display and "No risks" not in str(risks_display):
        completeness += 25

    return (
        master_json,
        overview_empty_update,
        overview_output_update,
        checklist_empty_update,
        checklist_output_update,
        timeline_empty_update,
        timeline_output_update,
        risks_display,
        verification_empty_update,
        verification_output_update,
        verification_summary_update,
        gr.update(value=f"✅ Ready · Completeness {completeness}%", visible=True),
        gr.update(value=[], visible=False),
    )


def run_eligibility_check(income, master_json):
    if not master_json:
        return "ℹ Upload a form first."
    return check_eligibility(master_json, income)


def run_verification(files, master_json):
    # Gradio may return a File object or list depending on browser upload.
    # Normalize to list for reliable truthiness checks.
    if not master_json:
        return (
            gr.update(value="ℹ Upload supporting documents to verify.", visible=True),
            gr.update(visible=False),
            gr.update(value="", visible=False),
        )

    if files is None:
        files_list = []
    elif isinstance(files, list):
        files_list = files
    else:
        files_list = [files]

    if len(files_list) == 0:
        return (
            gr.update(value="ℹ Upload supporting documents to verify.", visible=True),
            gr.update(visible=False),
            gr.update(value="", visible=False),
        )


    if not files:
        return (
            gr.update(value="ℹ Upload supporting documents to verify.", visible=True),
            gr.update(visible=False),
            gr.update(value="", visible=False),
        )

    results = verify_documents(files_list, master_json)

    summary = verification_summary(results)

    return (
        gr.update(visible=False),
        gr.update(value=results, visible=True),
        gr.update(value=summary, visible=True),
    )


def run_qa(question: str, master_json: dict, chat_history):
    """Chat handler for gr.Chatbot.

    Gradio 6.x expects Chatbot value to be either:
    - list[dict{"role": "user"|"assistant", "content": "..."}]
    - or list[gr.ChatMessage]

    We normalize to dict format to avoid "messages format" errors.
    """

    if not master_json:
        assistant = "ℹ Upload a form first."
    else:
        prompt = json.dumps({"question": question, "master_json": master_json})
        assistant = ask_llm(prompt)

    # Normalize incoming history
    history = chat_history if isinstance(chat_history, list) else []

    def _to_msg(msg):
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            return msg
        # Some older formats may come as (user, assistant) tuples.
        if isinstance(msg, (list, tuple)) and len(msg) == 2:
            return {"role": "user", "content": str(msg[0])}
        return None

    norm_history: List[Dict[str, str]] = []
    for m in history:
        if isinstance(m, dict) and "role" in m and "content" in m:
            norm_history.append({"role": m["role"], "content": m["content"]})

    # Append new turn
    norm_history.append({"role": "user", "content": str(question)})
    norm_history.append({"role": "assistant", "content": str(assistant)})

    # Second output clears the textbox.
    return norm_history, ""


with gr.Blocks(title="PaperPilot") as demo:
    master_json_state = gr.State()

    with gr.Group(elem_id="appbar"):
        gr.HTML(
            """
            <div class="appbar">
              <div class="appbar-left">
                <div class="brand-mark">📄</div>
                <div class="brand-text">
                  <div class="brand-title">PaperPilot</div>
                  <div class="brand-subtitle">AI-powered scholarship & form assistant</div>
                </div>
              </div>
              <div class="appbar-right">
                <div class="status-active" id="status-pill" aria-label="Active">● Active</div>

              </div>
            </div>
            """
        )

    with gr.Tabs(elem_id="pp-tabs"):

        with gr.Tab("1) Analyze"):
            with gr.Row(equal_height=True):
                with gr.Column(scale=1):
                    with gr.Group(elem_id="card-upload", elem_classes=["pp-card"]):
                        gr.HTML(
                            """
                            <div class="card-header">
                              <div class="card-title">📤 Upload & Analyze</div>
                              <div class="card-subtitle">Start here</div>
                            </div>
                            """
                        )
                        file_input = gr.File(label="Form file (PDF / image)", file_count="single")
                        analyze_btn = gr.Button("Analyze Form", variant="primary")
                        clear_btn = gr.Button("Clear", variant="secondary")
                        with gr.Accordion("ℹ What happens", open=False):
                            gr.Markdown(
                                """
                                - Extract text (OCR/PDF)
                                - Build structured JSON
                                - Generate: overview, checklist, timeline, risk alerts
                                - Enable eligibility + document verification
                                """
                            )

                with gr.Column(scale=2):
                    with gr.Group(elem_classes=["pp-card"], elem_id="card-overview"):
                        gr.HTML(
                            """
                            <div class="card-header">
                              <div class="card-title">📋 Overview</div>
                              <div class="card-subtitle">Extracted summary</div>
                            </div>
                            """
                        )
                        overview_empty = gr.Markdown(
                            "ℹ Upload a form first.", visible=True, elem_classes=["pp-empty"]
                        )
                        overview_output = gr.Markdown("", visible=False)

                    with gr.Row(equal_height=True):
                        with gr.Group(elem_classes=["pp-card"], elem_id="card-risks"):
                            gr.HTML(
                                """
                                <div class="card-header">
                                  <div class="card-title">⚠ Risk Alerts</div>
                                  <div class="card-subtitle">Potential gaps</div>
                                </div>
                                """
                            )
                            risk_output = gr.Markdown("ℹ No risks detected.", elem_classes=["pp-empty"])

                        with gr.Group(elem_classes=["pp-card"], elem_id="card-timeline"):
                            gr.HTML(
                                """
                                <div class="card-header">
                                  <div class="card-title">📅 Timeline</div>
                                  <div class="card-subtitle">Important dates</div>
                                </div>
                                """
                            )
                            timeline_empty = gr.Markdown(
                                "ℹ No timeline information found in this form.",
                                visible=True,
                                elem_classes=["pp-empty"],
                            )
                            timeline_output = gr.DataFrame(
                                headers=["Date", "Event"],
                                label="",
                                visible=False,
                            )

        with gr.Tab("2) Checklist"):
            with gr.Row(equal_height=True):
                with gr.Column(scale=2):
                    with gr.Group(elem_classes=["pp-card"], elem_id="card-checklist"):
                        gr.HTML(
                            """
                            <div class="card-header">
                              <div class="card-title">📑 Document Checklist</div>
                              <div class="card-subtitle">From extracted requirements</div>
                            </div>
                            """
                        )
                        checklist_empty = gr.Markdown(
                            "ℹ Analyze a form to see results.",
                            visible=True,
                            elem_classes=["pp-empty"],
                        )
                        checklist_output = gr.DataFrame(
                            headers=["Documents", "Status"],
                            label="",
                            visible=False,
                        )

        with gr.Tab("3) Eligibility & Verify"):
            with gr.Row(equal_height=True):
                with gr.Column(scale=1):
                    with gr.Group(elem_classes=["pp-card"], elem_id="card-eligibility"):
                        gr.HTML(
                            """
                            <div class="card-header">
                              <div class="card-title">💳 Eligibility</div>
                              <div class="card-subtitle">Income-based check</div>
                            </div>
                            """
                        )
                        income_input = gr.Number(label="Annual Family Income (₹)", precision=0)
                        check_btn = gr.Button("Check Eligibility", variant="primary")
                        eligibility_output = gr.Markdown("ℹ Upload a form first.", elem_classes=["pp-empty"])

                with gr.Column(scale=2):
                    with gr.Group(elem_classes=["pp-card"], elem_id="card-verification"):
                        gr.HTML(
                            """
                            <div class="card-header">
                              <div class="card-title">📁 Document Verification</div>
                              <div class="card-subtitle">Upload supporting files</div>
                            </div>
                            """
                        )
                        verify_upload = gr.File(file_count="multiple", label="Supporting documents")
                        verify_btn = gr.Button("Verify Documents", variant="primary")
                        verification_empty = gr.Markdown(
                            "ℹ Upload supporting documents to verify.",
                            visible=True,
                            elem_classes=["pp-empty"],
                        )
                        verification_output = gr.DataFrame(
                            headers=["Document", "Status"],
                            label="",
                            visible=False,
                        )
                        verification_summary_output = gr.Markdown(visible=False)

        with gr.Tab("4) Ask PaperPilot"):
            with gr.Group(elem_classes=["pp-card"], elem_id="card-qa"):
                gr.HTML(
                    """
                    <div class="card-header">
                      <div class="card-title">💬 Ask PaperPilot</div>
                      <div class="card-subtitle">Questions based on your extracted form</div>
                    </div>
                    """
                )
                chat_output = gr.Chatbot(value=[], elem_id="qa-chat", height=320)

                with gr.Row(equal_height=False):
                    question_input = gr.Textbox(
                        label="Your question",
                        placeholder="e.g., What documents are required? What is the deadline?",
                        scale=4,
                    )
                    ask_btn = gr.Button("Send", variant="primary", scale=1)

                gr.Markdown(
                    """
                    **Try:** What is the eligibility criteria? What documents are needed? What should I do next?
                    """,
                    elem_classes=["pp-muted"],
                )

    # Footer
    gr.Markdown(
        """
        <div class="custom-footer">
          Built with ❤️ using: Gradio • EasyOCR • PyMuPDF • Python
          <br/><b>PaperPilot</b> – Helping users understand forms effortlessly.
        </div>
        """,
        elem_classes=["custom-footer"],
    )

    # Handlers
    analyze_btn.click(
        fn=analyze_document,
        inputs=[file_input],
        outputs=[
            master_json_state,
            overview_empty,
            overview_output,
            checklist_empty,
            checklist_output,
            timeline_empty,
            timeline_output,
            risk_output,
            verification_empty,
            verification_output,
            verification_summary_output,
            gr.State(),
            gr.State(),
        ],
    )

    def _clear_all():
        return (
            {},
            gr.update(value="ℹ Upload a form first.", visible=True),
            gr.update(visible=False),
            gr.update(value="ℹ Analyze a form to see results.", visible=True),
            gr.update(visible=False),
            gr.update(value="ℹ No timeline information found in this form.", visible=True),
            gr.update(visible=False),
            "ℹ No risks detected.",
            gr.update(value="ℹ Upload supporting documents to verify.", visible=True),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            gr.update(value="ℹ Ready", visible=True),
            [],
        )

    # NOTE: Clear is optional; leaving it disabled avoids risking wiring mismatch.
    # clear_btn.click(fn=_clear_all, inputs=[], outputs=[])

    check_btn.click(
        fn=run_eligibility_check,
        inputs=[income_input, master_json_state],
        outputs=eligibility_output,
    )

    verify_btn.click(
        fn=run_verification,
        inputs=[verify_upload, master_json_state],
        outputs=[verification_empty, verification_output, verification_summary_output],
    )

    ask_btn.click(
        fn=run_qa,
        inputs=[question_input, master_json_state, chat_output],
        outputs=[chat_output, question_input],
    )

    question_input.submit(
        fn=run_qa,
        inputs=[question_input, master_json_state, chat_output],
        outputs=[chat_output, question_input],
    )


demo.launch(theme=gr.themes.Soft(), css=_read_css())

