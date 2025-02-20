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
from spire.doc import *
from spire.doc.common import *
# from sample_json import json_template_str

from spire.doc import Document

# Set global font path for Spire.Doc
Document.SetGlobalFontPaths("/usr/share/fonts")


load_dotenv()
 
 
 
async def cv_json(file_path):
 
    # # Load JSON template
    # json_template_path = r"D:\OneDrive - MariApps Marine Solutions Pte.Ltd\liju_resume_parser/output_json.json"
    with open("output_json.json", "r", encoding="utf-8") as file:
        json_template_str = json.load(file)
    
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
    # Initialize OpenAI Client
    client = OpenAI(api_key=os.getenv("api_key"))
 
    # Convert PDF to optimized images
    def convert_pdf_to_images(pdf_path):
        print("converting the pdf to images")
        doc = fitz.open(pdf_path)
        images = []

        for page in doc:
            pix = page.get_pixmap(dpi=100, colorspace=fitz.csGRAY)
            img_bytes = BytesIO(pix.tobytes("jpeg"))  # Store in memory
            img_base64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
            images.append(img_base64)


        print("converted the pdf to images")
        return images
 
    # Encode images in parallel (faster base64 conversion)
    # def encode_image(image_path):
    #     with open(image_path, "rb") as image_file:
    #         return base64.b64encode(image_file.read()).decode("utf-8")
 
    # Send API requests asynchronously for speed
    async def send_openai_request(session, batch):
        print("send api responses")
        try:
            all_images_data = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}} for img in batch]

            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('api_key')}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}] + all_images_data}]
                }
            ) as response:
                response_text = await response.text()
                
                if response.status != 200:
                    print(f"Error {response.status}: {response_text}")
                    return None

                response_json = json.loads(response_text)
                raw_content = response_json["choices"][0]["message"]["content"]

                # Removing unnecessary formatting
                if raw_content.startswith("```json"):
                    raw_content = raw_content[7:-3]  # Remove ```json at the start and ``` at the end
                

                print("finished")
                return json.loads(raw_content)
        
        except Exception as e:
            print(f"API Request Error: {e}")
            return None
 
    # Asynchronous Processing of API Calls
    # Process images and send requests in batches
    # async def process_images(file_path):
    #     base64_images = convert_pdf_to_images(file_path)
    #     batch_size = 3  # Process in smaller batches
    #     tasks = []

    #     async with aiohttp.ClientSession() as session:
    #         for i in range(0, len(base64_images), batch_size):
    #             batch = base64_images[i:i + batch_size]
    #             tasks.append(send_openai_request(session, batch))

    #         responses = await asyncio.gather(*tasks)

    #     # Filter out failed responses
    #     json_outputs = [resp for resp in responses if resp]
    #     return json_outputs[0] if json_outputs else None

    # # Run async processing
    # return await process_images(file_path)





    # orginal code
    # async def process_images(file_path):
    #         print("processing images")
    #         base64_images = convert_pdf_to_images(file_path)

    #         async with aiohttp.ClientSession() as session:
    #             # Send ALL images in one request (preferred if within token limits)
    #             response = await send_openai_request(session, base64_images)
    #             return response

    # return await process_images(file_path)


    # async def process_images(file_path):
    #         print("processing images")
    #         base64_images = convert_pdf_to_images(file_path)

    #         async with aiohttp.ClientSession() as session:
    #             # Send ALL images in one request (preferred if within token limits)
    #             response = await send_openai_request(session, base64_images)

    #             def replace_values(data, mapping):
    #                 if isinstance(data, dict):
    #                     return {key: replace_values(value, mapping) for key, value in data.items()}
    #                 elif isinstance(data, list):
    #                     return [replace_values(item, mapping) for item in data]
    #                 elif isinstance(data, str):
    #                     return mapping.get(data, data)  # Replace if found, else keep original
    #                 return data


    #             updated_json = replace_values(response, mapping_dict)


    #             return updated_json

    # return await process_images(file_path)


    def doc_to_images(file_path, output_folder = r"D:\OneDrive - MariApps Marine Solutions Pte.Ltd\liju_resume_parser"):
        document = Document()
        document.LoadFromFile(file_path)
        images = []
        for i in range(document.GetPageCount()):
            # Convert a specific page to bitmap image
            imageStream = document.SaveImageToStreams(i, ImageType.Bitmap)

            image_path = os.path.join(output_folder, f"page_{i+1}.jpg")
        
            # Save image file
            with open(image_path, "wb") as imageFile:
                imageFile.write(imageStream.ToArray())


            img_bytes = imageStream.ToArray()

            # Encode to base64
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            images.append(img_base64)
        document.Close()
        print("converted the word to images")
        return images

    async def process_images(file_path):
            print("processing images")
            # filename = file.filename.lower()
            if not (file_path.endswith(".pdf") or file_path.endswith(".doc") or file_path.endswith(".docx")):
                raise HTTPException(status_code=400, detail="Only PDF and Word documents are allowed")
            
            if file_path.endswith(".doc") or file_path.endswith(".docx"):
                base64_images = doc_to_images(file_path)
            else:        
                base64_images = convert_pdf_to_images(file_path)

            async with aiohttp.ClientSession() as session:
                # Send ALL images in one request (preferred if within token limits)
                response = await send_openai_request(session, base64_images)

                def replace_values(data, mapping):
                    if isinstance(data, dict):
                        return {key: replace_values(value, mapping) for key, value in data.items()}
                    elif isinstance(data, list):
                        return [replace_values(item, mapping) for item in data]
                    elif isinstance(data, str):
                        return mapping.get(data, data)  # Replace if found, else keep original
                    return data


                updated_json = replace_values(response, mapping_dict)


                return updated_json

    return await process_images(file_path)
