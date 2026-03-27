# Synapsians — UKW Exam Evaluator

An AI-powered tool that evaluates university medical exam documents (`.docx`) for structural, formatting, and didactic rule violations. Feedback is injected as native Microsoft Word comments.

## Architecture

```
frontend/          → Static HTML/CSS/JS UI (Three.js 3D background)
backend/           → Python FastAPI server
  ├── main.py              → API endpoints (/evaluate, /status)
  ├── document_processor.py → DOCX parsing, question extraction, comment injection
  ├── llm_engine.py        → Azure OpenAI integration (base + fine-tuned models)
  ├── rules_engine.py      → Rule-based formatting checks
  └── progress.py          → Real-time progress state
data/              → Exam files, templates, and fine-tuning datasets
```

## Setup

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Create .env in project root
echo 'AZURE_OPENAI_API_KEY=your-key-here' > ../.env

# Run backend
uvicorn main:app --reload --env-file ../.env

# Frontend (separate terminal)
cd frontend
python -m http.server 3000
```

Open `http://localhost:3000` in your browser.

## Models

| Toggle | Model | Description |
|--------|-------|-------------|
| Default | `gpt-4o` | Base model |
| Tab key | `gpt-4o-exam-linter-v2` | Fine-tuned on annotated exam data |

Press **Tab** in the browser to toggle between base and fine-tuned model.

## API

```
POST /evaluate?FINETUNED_MODEL2=true   → Upload .docx, get evaluated .docx back
GET  /status                            → Poll processing progress
```
