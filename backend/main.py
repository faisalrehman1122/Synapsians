from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from document_processor import process_exam_document
import uvicorn
import progress

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
def get_status():
    return progress.current_status

@app.post("/evaluate")
async def evaluate_exam(file: UploadFile = File(...)):
    progress.current_status["message"] = "Uploading File & Initializing..."
    progress.current_status["progress"] = 5
    
    if not file.filename.endswith(".docx"):
        return {"error": "Invalid file format. Only .docx files are supported."}
        
    file_bytes = await file.read()
    
    # Process document
    progress.current_status["message"] = "Analyzing document structure..."
    progress.current_status["progress"] = 10
    modified_docx_bytes = await process_exam_document(file_bytes)
    
    progress.current_status["message"] = "Process Complete!"
    progress.current_status["progress"] = 100
    
    # Return as downloadable file
    return Response(
        content=modified_docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="evaluated_{file.filename}"'}
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
