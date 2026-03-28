# Synapsians — UKW Exam Evaluator 🎓

An AI-powered tool built for the **University of Würzburg (UKW)** that automatically evaluates medical multiple-choice exam documents (`.docx`) for structural, formatting, and didactic rule violations. Expert feedback is injected directly as native **Microsoft Word comments** — the original document content remains untouched.

---

## ✨ Features

- **Upload & Evaluate** — Drag-and-drop a `.docx` exam file and receive an annotated copy with Word comments
- **Rule-Based Checks** — Python engine validates formatting (fonts, margins, bolding, structure)
- **AI-Powered Analysis** — Azure OpenAI GPT models check for didactic rule violations:
  - Absolute words (`immer`, `nie`, `alle`, `ausschließlich`, `stets`, `kein`)
  - Double negations
  - Length cues (one option noticeably longer than others)
  - Word-stem cues (question stem word repeated only in correct answer)
  - Question type math rules (PickS, Kprim, TypA)
- **3 Model Modes** — Toggle between Base GPT-4o, Fine-tuned v1, and Fine-tuned v2 with the `Tab` key
- **Real-Time Progress** — Live question-by-question processing visualization with animated 3D background
- **Parallel Processing** — Up to 10 concurrent API calls for fast evaluation

---

## 🏗️ Architecture

```
synapsians/
├── frontend/                  → Static HTML/CSS/JS UI
│   ├── index.html             → Main page with drag-and-drop upload
│   ├── style.css              → Styling with animations
│   └── app.js                 → Three.js 3D background + app logic
│
├── backend/                   → Python FastAPI server
│   ├── main.py                → API endpoints (/evaluate, /status)
│   ├── document_processor.py  → DOCX parsing, question extraction, comment injection
│   ├── llm_engine.py          → Azure OpenAI integration (base + fine-tuned models)
│   ├── rules_engine.py        → Rule-based formatting checks
│   ├── progress.py            → Real-time progress tracking state
│   ├── generate_ft_data.py    → Script: DOCX → JSONL (fine-tuning data v1)
│   └── generate_ft_data2.py   → Script: Annotated PDF → JSONL (fine-tuning data v2)
│
├── data/
│   ├── Selektion Klausuren Hackathon ki/  → Source exam DOCX files
│   ├── ft_dataset_pdf/        → Annotated PDF exams (with expert comments)
│   ├── ft_data/               → Fine-tuning dataset v1 (JSONL)
│   ├── ft_data2/              → Fine-tuning dataset v2 (JSONL)
│   ├── Formatierungshinweise/ → Formatting guidelines
│   ├── Frageformate/          → Question format documentation
│   └── Vorlagen/              → Templates
│
└── .env                       → Azure OpenAI API key (not committed)
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- An Azure OpenAI API key

### Installation

```bash
# Clone the repository
git clone git@github.com:faisalrehman1122/Synapsians.git
cd Synapsians

# Set up environment
echo 'AZURE_OPENAI_API_KEY=your-key-here' > .env

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running

Open **two terminals**:

```bash
# Terminal 1 — Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --env-file ../.env
```

```bash
# Terminal 2 — Frontend
cd frontend
python -m http.server 3000
```

Open **http://localhost:3000** in your browser.

---

## 🤖 Models

| Toggle (Tab Key) | Deployment | Description |
|---|---|---|
| Base | `gpt-4o` | Base GPT-4o model |
| Fine-tuned v1 | `gpt-4o-2024-08-06-exam-linter-v1` | Fine-tuned on raw DOCX questions |
| **Fine-tuned v2** ⭐ | `gpt-4o-2024-08-06-exam-linter-v2` | Fine-tuned on expert-annotated PDF exams |

> **v2 outperforms both the base model and v1** by learning directly from expert reviewer comments.

Press **Tab** in the browser to cycle between models. The active model is shown briefly on screen.

---

## 🔌 API

| Endpoint | Method | Description |
|---|---|---|
| `/evaluate` | `POST` | Upload `.docx` file, returns evaluated `.docx` with Word comments |
| `/status` | `GET` | Poll real-time processing progress |

### Query Parameters for `/evaluate`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `FINETUNED_MODEL` | bool | `false` | Use fine-tuned model v1 |
| `FINETUNED_MODEL2` | bool | `false` | Use fine-tuned model v2 |

Example:
```bash
curl -X POST "http://127.0.0.1:8000/evaluate?FINETUNED_MODEL2=true" \
  -F "file=@exam.docx" -o evaluated_exam.docx
```

---

## 📊 Fine-Tuning Data

Two scripts generate training data in OpenAI Chat Completion JSONL format:

| Script | Source | Output |
|---|---|---|
| `generate_ft_data.py` | Raw DOCX exams → GPT-4o baseline responses | `data/ft_data/` |
| `generate_ft_data2.py` | Annotated PDFs → expert comments as gold labels | `data/ft_data2/` |

Each JSONL file contains `{"messages": [system, user, assistant]}` entries ready for Azure OpenAI fine-tuning.

---

## 🛠️ Tech Stack

- **Frontend**: HTML, CSS, JavaScript, Three.js
- **Backend**: Python, FastAPI, Uvicorn
- **AI**: Azure OpenAI (GPT-4o + fine-tuned models)
- **Document Processing**: python-docx, PyMuPDF, markdownify
