import os
import base64
import fitz  # PyMuPDF
import json
import asyncio
import aiohttp  # Async HTTP for OpenAI API
from dotenv import load_dotenv
from openai import OpenAI
from io import BytesIO
from dict_file import mapping_dict
from fastapi import HTTPException
import subprocess
import platform
import aiofiles

load_dotenv()

async def cv_json(file_path):
    # Load JSON template
    async with aiofiles.open("output_json.json", "r", encoding="utf-8") as file:
        json_template_str = json.loads(await file.read())

    # Optimized Prompt
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

    print(prompt)
    client = OpenAI(api_key=os.getenv("api_key"))

    


    # Convert PDF to optimized images (Async version)
    async def convert_pdf_to_images(pdf_path):
        print("Converting the PDF to images")
        doc = await asyncio.to_thread(fitz.open, pdf_path)  # Run in separate thread
        images = []
    
        for page in doc:
            pix = await asyncio.to_thread(page.get_pixmap, dpi=100, colorspace=fitz.csGRAY)  # Run in separate thread
            img_bytes = BytesIO(pix.tobytes("jpeg"))  # Store in memory
            img_base64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
            images.append(img_base64)
    
        print("Converted the PDF to images")
        return images
    
    
    # Convert DOCX to PDF (Async version)
    async def convert_docx_to_pdf(docx_path):
        """ Converts DOCX to PDF using LibreOffice (Linux) or Microsoft Word (Windows). """
        pdf_path = docx_path.replace(".docx", ".pdf")
    
        try:
            if platform.system() == "Windows":
                import win32com.client
                word = win32com.client.Dispatch("Word.Application")
                doc = word.Documents.Open(os.path.abspath(docx_path))
                doc.SaveAs(os.path.abspath(pdf_path), FileFormat=17)  # PDF format
                doc.Close()
                word.Quit()
                print(f" Converted {docx_path} to {pdf_path} using Microsoft Word")
            else:
                libreoffice_path = "/usr/bin/libreoffice"
                if not os.path.exists(libreoffice_path):
                    raise FileNotFoundError(f"LibreOffice not found at {libreoffice_path}")
    
                process = await asyncio.create_subprocess_exec(
                    libreoffice_path, "--headless", "--convert-to", "pdf",
                    "--outdir", os.path.dirname(docx_path), docx_path
                )
                await process.communicate()  # Ensure subprocess completes
    
                print(f" Converted {docx_path} to {pdf_path} using LibreOffice")
    
            return pdf_path
        except Exception as e:
            print(f" DOCX to PDF conversion failed: {e}")
            raise HTTPException(status_code=500, detail=f"DOCX to PDF conversion failed: {e}")
    
    
    # Convert DOCX to Images (Async version)
    async def doc_to_images(file_path):
        """ Converts DOCX to PDF and then to images asynchronously. """
        try:
            pdf_file_path = await convert_docx_to_pdf(file_path)
            if not pdf_file_path:
                raise HTTPException(status_code=500, detail="DOCX to PDF conversion failed")
    
            images = await convert_pdf_to_images(pdf_file_path)
            print(" Converted DOCX to images")
            return images
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DOCX to images conversion failed: {str(e)}")
    
    
    # Send API requests asynchronously for speed
    async def send_openai_request(session, batch, prompt):
        print("Sending API requests")
        try:
            all_images_data = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}} for img in batch]
    
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('api_key')}", "Content-Type": "application/json"},
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}] + all_images_data}]}
            ) as response:
                response_text = await response.text()
                
                if response.status != 200:
                    print(f"Error {response.status}: {response_text}")
                    return None
    
                response_json = json.loads(response_text)
                raw_content = response_json["choices"][0]["message"]["content"]
    
                if raw_content.startswith("```json"):
                    raw_content = raw_content[7:-3]  # Remove ```json at the start and ``` at the end
    
                print("Finished processing OpenAI response")
                return json.loads(raw_content)
        
        except Exception as e:
            print(f"API Request Error: {e}")
            return None
    
    
    # Process images and extract data asynchronously
    async def process_images(file_path):
        print("Processing images")
        
        if not (file_path.endswith(".pdf") or file_path.endswith(".doc") or file_path.endswith(".docx")):
            raise HTTPException(status_code=400, detail="Only PDF and Word documents are allowed")
    
        if file_path.endswith(".doc") or file_path.endswith(".docx"):
            base64_images = await doc_to_images(file_path)  # Ensure async call
        else:
            base64_images = await convert_pdf_to_images(file_path)  # Ensure async call
    
        async with aiohttp.ClientSession() as session:
            response = await send_openai_request(session, base64_images, prompt)
    
            def replace_values(data, mapping):
                if isinstance(data, dict):
                    return {key: replace_values(value, mapping) for key, value in data.items()}
                elif isinstance(data, list):
                    return [replace_values(item, mapping) for item in data]
                elif isinstance(data, str):
                    return mapping.get(data, data)
                return data
    
            updated_json = replace_values(response, mapping_dict)
            return updated_json

    return await process_images(file_path)
