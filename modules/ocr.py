import pdfplumber
import easyocr
import fitz
import re
import numpy as np


reader = easyocr.Reader(['en'])


def clean_text(text):
    """
    Clean extracted text while preserving useful structure.
    """

    text = re.sub(r'[ \t]+', ' ', text)

    text = re.sub(r'\n+', '\n', text)

    return text.strip()


def extract_pdf_text(pdf_path):
    """
    Extract selectable text using pdfplumber.
    """

    text = ""

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return clean_text(text)


def extract_scanned_pdf_text(pdf_path):
    """
    OCR fallback for scanned PDFs using
    PyMuPDF + EasyOCR.
    """
    print("Opening PDF...")

    doc = fitz.open(pdf_path)

    text = ""

    print(f"Pages found: {len(doc)}")

    for page_num in range(1, len(doc)):

        print(f"Processing page {page_num + 1}")

        page = doc.load_page(page_num)

        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))

        img = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        )

        img = img.reshape(
            pix.height,
            pix.width,
            pix.n
        )

        results = reader.readtext(
            img,
            detail=0
        )

        text += " ".join(results)
        text += "\n"

    doc.close()

    return clean_text(text)


def extract_text_from_pdf(pdf_path):

    text = extract_pdf_text(pdf_path)

    if len(text.strip()) > 50:
        return text

    print("Scanned PDF detected. Running OCR...")

    return extract_scanned_pdf_text(pdf_path)


def extract_text_from_image(image_path):

    results = reader.readtext(
        image_path,
        detail=0
    )

    text = " ".join(results)

    return clean_text(text)


def extract_text(file_path):

    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)

    return extract_text_from_image(file_path)