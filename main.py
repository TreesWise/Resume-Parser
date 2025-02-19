from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
from cv_json_smalll_prompt import cv_json
# import cv_json
from spire.doc import *
from spire.doc.common import *
 
app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# @app.post("/upload/")
# async def upload_file(file: UploadFile = File(...)):
#     try:
#         filename = file.filename.lower()
#         if not (filename.endswith(".pdf") or filename.endswith(".doc") or filename.endswith(".docx")):
#             raise HTTPException(status_code=400, detail="Only PDF and Word documents are allowed")

#         file_path = os.path.join(UPLOAD_DIR, file.filename)
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         # Convert DOCX to PDF if necessary
#         if filename.endswith(".doc") or filename.endswith(".docx"):
#             try:
#                 from docx2pdf import convert
#                 pdf_file_path = os.path.splitext(file_path)[0] + ".pdf"
#                 convert(file_path, pdf_file_path)
#                 file_path = pdf_file_path  # Use the converted PDF for processing
#             except Exception as e:
#                 raise HTTPException(status_code=500, detail=f"DOCX to PDF conversion failed: {str(e)}")

#         # Process the file
#         extracted_json = await cv_json(file_path)

#         if not extracted_json:
#             raise HTTPException(status_code=500, detail="Failed to extract data. JSON response is empty.")

#         return JSONResponse(content=extracted_json)
    
#     except Exception as e:
#         print(f"Error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))




@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        filename = file.filename.lower()
        if not (filename.endswith(".pdf") or filename.endswith(".doc") or filename.endswith(".docx")):
            raise HTTPException(status_code=400, detail="Only PDF and Word documents are allowed")

        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        extracted_json = await cv_json(file_path)

        if not extracted_json:
            raise HTTPException(status_code=500, detail="Failed to extract data. JSON response is empty.")

        return JSONResponse(content=extracted_json)
    
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))