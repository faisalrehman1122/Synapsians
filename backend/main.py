from fastapi import FastAPI, UploadFile, File, Query
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
async def evaluate_exam(
    file: UploadFile = File(...),
    FINETUNED_MODEL: bool = Query(False, description="Use fine-tuned model v1"),
    FINETUNED_MODEL2: bool = Query(False, description="Use fine-tuned model v2")
):
    # Reset all state for this new run
    progress.reset()
    progress.current_status["message"]  = "Uploading & initialising…"
    progress.current_status["progress"] = 5
    progress.current_status["phase"]    = "uploading"

    if not file.filename.endswith(".docx"):
        return {"error": "Invalid file format. Only .docx files are supported."}

    # Determine which model to use (v2 takes priority if both are set)
    if FINETUNED_MODEL2:
        model_version = "v2"
    elif FINETUNED_MODEL:
        model_version = "v1"
    else:
        model_version = "base"

    file_bytes = await file.read()

    progress.current_status["message"]  = f"Analysing document structure (Model: {model_version})…"
    progress.current_status["progress"] = 10
    progress.current_status["phase"]    = "parsing"

    modified_docx_bytes = await process_exam_document(file_bytes, model_version=model_version)

    progress.current_status["message"]  = "Complete!"
    progress.current_status["progress"] = 100
    progress.current_status["phase"]    = "complete"

    return Response(
        content=modified_docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="evaluated_{file.filename}"'}
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
