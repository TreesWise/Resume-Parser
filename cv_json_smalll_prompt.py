import os
import base64
import fitz  # PyMuPDF
import json
import asyncio
import aiohttp  # Async HTTP for OpenAI API
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from openai import OpenAI
from io import BytesIO
from dict_file import mapping_dict
from fastapi import HTTPException
import subprocess  # Used for calling pandoc
import tempfile
import google.generativeai as genai

load_dotenv()

async def cv_json(file_path):

    with open("output_json.json", "r", encoding="utf-8") as file:
        json_template_str = json.load(file)
    
    prompt = f"""
    You are an expert in data extraction and JSON formatting. Your task is to extract and format resume data **exactly** as per the provided JSON template `{json_template_str}`. Ensure strict compliance with structure, accuracy, and completeness. Follow these rules carefully:
    ### **Extraction Guidelines:**
    1. **Strict JSON Compliasnce:**
    - Every key in smaple JSON must be present, even if values are `null`. 
    - Maintain exact order and structure—no extra details or modifications.
    - Tables (`basic_details`, `experience_table`, `certificate_table`) should strictly follow the provided format.  
    2. **Data Handling Rules:**
    - **basic_details:**  Extract and correctly map `City`, `State`, `Country`, Zipcode, and split the address into Address1–Address4.
    - **Experience Table:**
        - Merge multi-line entries into complete, single values.
        - Ensure `TEU` (container capacity) is numerical and `IMO` is a 7-digit number. If missing, set to `null`.
        - Ensure `Flag` values are valid country names (e.g., "Panama"), otherwise set to `null`.
        - Extract the experience section first before processing other tables to avoid token loss.
         ### **Important:** Ensure **every experience entry** is captured fully, no matter how fragmented, and no entries are omitted. Return **only** the structured JSON output.
         - **Experience Table:**  It is *absolutely crucial* that *every single* experience entry is extracted, no matter how fragmented or poorly formatted it appears in the resume.  Do not omit any experience entries.  If an entry spans multiple lines, merge those lines to create a complete entry.  Double-check your output against the original resume to ensure no experience details are missing.
    - **Certificate Table:**
        - Extract **all** certificates, **visas**, **passports**, and **flag documents**, even if scattered or multi-line.
        - Merge related certificates into a single entry (e.g., "GMDSS ENDORSEMENT").
        - If details like `NUMBER`, `ISSUING VALIDATION DATE`, or `ISSUING PLACE` are missing, set them to `null`.
        - Include documents like **National Documents** (e.g., "SEAFARER’S ID", "TRAVELLING PASSPORT "), **LICENCE** (e.g., "National License (COC)", "GMDSS "), **FLAG DOCUMENTS** (e.g., "Liberian"), **MEDICAL DOCUMENTS** (e.g., "Yellow Fever") in this section. Don't omit any of these documents.
        - If a certificate's NUMBER is **N/A**, do not include that certificate entry in the extracted JSON output; if the NUMBER is missing or empty, it can be included with null as the value.
        - **Certificate Table:**  Ensure that *all* certificates, visas, passports, and flag documents are extracted.  Pay close attention to certificates that might be spread across multiple lines or sections of the resume.  Do not miss any certificates.  If a certificate's details (number, issuing date, place) are missing, use `null` for those fields, but *do not omit the certificate entry itself*.
    3. **Ensuring Accuracy & Completeness:**
    - Scan the entire resume to ensure **no omissions** in `certificate_table`.
    - Maintain original sequence—do not alter entry order.
    - Do **not** include irrelevant text, extra fields, or unrelated details.
    - If data is missing, return `null` but keep the field in the output.
    4. **Output Formatting:**
    - Generate **only** a properly structured JSON response (no extra text, explanations, or code blocks).
    - The JSON must be **clean, well-formatted, and validated** before returning.
    Strictly follow these instructions to ensure 100% accuracy in extraction. Return **only** the structured JSON output.
    """

    async def send_gemini_flash_request(file_path, prompt):
        print("Sending Gemini 2.0 Flash API request")
        genai.configure(api_key=os.getenv("api_key"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        with open(file_path, "rb") as file:
            document = genai.upload_file(file, display_name="Sample PDF", mime_type="application/pdf")
        try:
            response = model.generate_content([prompt, document])
            cleaned_string = response.text.strip("\njson\n").strip("\n").replace("'", '"').replace("None", "null")

            try:
                extracted_json = json.loads(cleaned_string)
                return json.dumps(extracted_json, indent=4)
            except json.JSONDecodeError as e:
                print("Error parsing JSON:", e)
        except Exception as e:
            print(f"API Request Error: {e}")
            return None

    def doc_to_pdf(file_path):
        try:
            temp_dir = tempfile.mkdtemp()  
            pdf_file_path = os.path.join(temp_dir, "converted.pdf")

            # Use Pandoc for conversion
            command = f"pandoc '{file_path}' -o '{pdf_file_path}'"
            subprocess.run(command, shell=True, check=True)

            if not os.path.exists(pdf_file_path):
                raise FileNotFoundError(f"PDF conversion failed, file not found: {pdf_file_path}")

            print(f"PDF successfully created: {pdf_file_path}")
            return pdf_file_path  
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DOCX to PDF conversion failed: {str(e)}")
            
    def replace_values(data, mapping):
        if isinstance(data, dict):
            return {mapping.get(key, key): replace_values(value, mapping) for key, value in data.items()}
        elif isinstance(data, list):
            return [replace_values(item, mapping) for item in data]
        elif isinstance(data, str):
            return mapping.get(data, data)  
        return data

    async def process_images(file_path, prompt):
        print("Processing images")

        if not (file_path.endswith(".pdf") or file_path.endswith(".doc") or file_path.endswith(".docx")):
            raise HTTPException(status_code=400, detail="Only PDF and Word documents are allowed")
        
        if file_path.endswith(".doc") or file_path.endswith(".docx"):
            file_path = doc_to_pdf(file_path)

        response = await send_gemini_flash_request(file_path, prompt)
        print("Response from Gemini:", response)
        updated_json = replace_values(response, mapping_dict)
        return updated_json

    return await process_images(file_path, prompt)
