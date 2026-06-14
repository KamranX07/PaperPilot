import os
import json
import re
import requests
from dotenv import load_dotenv
from modules.extractor import build_master_json
from modules.qa import answer_question

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

if not PROVIDER:
    if OPENAI_API_KEY:
        PROVIDER = "openai"
    elif HF_TOKEN:
        PROVIDER = "huggingface"
    else:
        PROVIDER = "local"

# Validate configuration
if PROVIDER == "huggingface" and not HF_TOKEN:
    print("Warning: Hugging Face provider selected but HF_TOKEN is missing. Falling back to local.")
    PROVIDER = "local"
elif PROVIDER == "openai" and not OPENAI_API_KEY:
    print("Warning: OpenAI provider selected but OPENAI_API_KEY is missing. Falling back to local.")
    PROVIDER = "local"
elif PROVIDER not in ["huggingface", "openai", "local"]:
    print(f"Warning: Unknown provider '{PROVIDER}'. Falling back to local.")
    PROVIDER = "local"

print(f"PaperPilot LLM Provider initialized with active mode: '{PROVIDER}'")


def parse_json_from_response(response_text):
    """
    Tries to extract and parse JSON from the LLM response.
    """
    response_clean = response_text.strip()
    try:
        return json.loads(response_clean)
    except json.JSONDecodeError:
        pass

    # Look for a markdown JSON code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_clean, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Look for the first '{' and last '}'
    start = response_clean.find('{')
    end = response_clean.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(response_clean[start:end+1])
        except json.JSONDecodeError:
            pass

    raise ValueError("Failed to extract valid JSON structure from LLM response")


def extract_form_data(text):
    """
    Extracts structured form data matching the MASTER_JSON_TEMPLATE schema.
    If no LLM provider is active or if the API call fails, falls back to the rule-based extractor.
    """
    if PROVIDER == "local":
        return build_master_json(text)

    schema_desc = """
    {
        "form_name": "Name of the form",
        "deadline": "Application deadline or important date (e.g. '15 August 2026' or 'Not Found')",
        "eligibility": "Brief explanation of eligibility criteria, including any income limits",
        "documents": ["List", "of", "required", "documents"],
        "contact_info": "Contact email, phone or address, or 'Not Found'",
        "summary": "A brief summary of the form"
    }
    """

    prompt = f"""You are an assistant that extracts structured information from form documents.
Analyze the following form text and extract the details. Return a valid JSON object strictly matching this schema:
{schema_desc}

Do not include any conversational text or explanation. Output ONLY the JSON block.

Form Text:
{text}
"""

    try:
        if PROVIDER == "huggingface":
            model_name = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
            headers = {"Authorization": f"Bearer {HF_TOKEN}"}
            api_url = f"https://api-inference.huggingface.co/models/{model_name}"
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 1024,
                    "temperature": 0.1,
                    "return_full_text": False
                }
            }
            response = requests.post(api_url, headers=headers, json=payload, timeout=45)
            response.raise_for_status()
            res_json = response.json()

            if isinstance(res_json, list) and len(res_json) > 0 and "generated_text" in res_json[0]:
                response_text = res_json[0]["generated_text"]
            elif isinstance(res_json, dict) and "generated_text" in res_json:
                response_text = res_json["generated_text"]
            else:
                raise ValueError(f"Unexpected Hugging Face API response: {res_json}")

        elif PROVIDER == "openai":
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a precise data extraction assistant that output JSON structure directly."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1
            }
            response = requests.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=45)
            response.raise_for_status()
            res_json = response.json()
            response_text = res_json["choices"][0]["message"]["content"]

        extracted_data = parse_json_from_response(response_text)

        # Build clean master_json dict to ensure all keys exist and formats match expectations
        cleaned_data = {}
        cleaned_data["form_name"] = str(extracted_data.get("form_name", "Unknown Form"))
        cleaned_data["deadline"] = str(extracted_data.get("deadline", "Not Found"))
        cleaned_data["eligibility"] = str(extracted_data.get("eligibility", "Not Found"))

        docs = extracted_data.get("documents", [])
        if isinstance(docs, list):
            cleaned_data["documents"] = [str(d).title() for d in docs]
        else:
            cleaned_data["documents"] = []

        cleaned_data["contact_info"] = str(extracted_data.get("contact_info", ""))
        cleaned_data["summary"] = str(extracted_data.get("summary", ""))

        return cleaned_data

    except Exception as e:
        print(f"Error extracting form data using LLM: {e}. Falling back to rule-based system.")
        return build_master_json(text)


def ask_llm(prompt):
    """
    Sends a prompt to the active LLM provider.
    Expects prompt to be either a plain text string or a JSON-serialized dictionary with 'question' and 'master_json'.
    Falls back to the rule-based QA system if no provider is available or on failure.
    """
    question = prompt
    master_json = {}

    # Try parsing the prompt as structured JSON containing question and master_json context
    try:
        data = json.loads(prompt)
        if isinstance(data, dict):
            question = data.get("question", prompt)
            master_json = data.get("master_json", {})
    except (json.JSONDecodeError, TypeError):
        pass

    if PROVIDER == "local":
        return answer_question(question, master_json)

    # Build standard QA context prompt for LLM
    formatted_prompt = (
        f"You are PaperPilot, an AI form assistant. Based on the extracted form details below, "
        f"answer the user's question accurately.\n\n"
        f"Form Context:\n{json.dumps(master_json, indent=2)}\n\n"
        f"Question: {question}\n\n"
        f"Answer:"
    )

    try:
        if PROVIDER == "huggingface":
            model_name = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
            headers = {"Authorization": f"Bearer {HF_TOKEN}"}
            api_url = f"https://api-inference.huggingface.co/models/{model_name}"
            payload = {
                "inputs": formatted_prompt,
                "parameters": {
                    "max_new_tokens": 512,
                    "temperature": 0.2,
                    "return_full_text": False
                }
            }
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            res_json = response.json()

            if isinstance(res_json, list) and len(res_json) > 0 and "generated_text" in res_json[0]:
                return res_json[0]["generated_text"].strip()
            elif isinstance(res_json, dict) and "generated_text" in res_json:
                return res_json["generated_text"].strip()
            else:
                raise ValueError(f"Unexpected Hugging Face API response: {res_json}")

        elif PROVIDER == "openai":
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are PaperPilot, a helpful AI assistant that answers questions based on extracted form data."},
                    {"role": "user", "content": formatted_prompt}
                ],
                "temperature": 0.2
            }
            response = requests.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(f"Error calling LLM provider '{PROVIDER}': {e}. Falling back to rule-based system.")
        return answer_question(question, master_json)
