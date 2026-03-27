import json
import concurrent.futures
from openai import AzureOpenAI
import logging
import os

ENDPOINT = "https://smartexamapp.openai.azure.com/"
API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
API_VERSION = "2024-12-01-preview"
DEPLOYMENT = "gpt-4o"

FT_API_VERSION = "2025-01-01-preview"
FT_DEPLOYMENT = "gpt-4o-2024-08-06-exam-linter-v1"

FT2_API_VERSION = "2025-01-01-preview"
FT2_DEPLOYMENT = "gpt-4o-2024-08-06-exam-linter-v2"

client = AzureOpenAI(
    api_version=API_VERSION,
    azure_endpoint=ENDPOINT,
    api_key=API_KEY
)

client_ft = AzureOpenAI(
    api_version=FT_API_VERSION,
    azure_endpoint=ENDPOINT,
    api_key=API_KEY
)

client_ft2 = AzureOpenAI(
    api_version=FT2_API_VERSION,
    azure_endpoint=ENDPOINT,
    api_key=API_KEY
)

def build_system_prompt(question_type):
    base_prompt = """
    You are a STRICT, algorithmic reviewer for medical multiple-choice exams.
    You MUST follow these rules exactly. DO NOT hallucinate rules or false positives.

    1. ABSOLUTE WORDS (STRICT WHITELIST):
    You may ONLY flag these EXACT 6 words: "immer", "nie", "alle", "ausschließlich", "stets", "kein".
    DO NOT flag verbs (e.g., "werden", "führt"). DO NOT flag adjectives (e.g., "reversibel", "identisch"). DO NOT flag nouns. 
    If a word is NOT in the 6-word list above, IT IS NOT AN ABSOLUTE WORD. DO NOT FLAG IT.

    2. DOUBLE NEGATIONS:
    Only flag true grammatical double negations (e.g., "keine unauffälligen"). A simple "nicht" is perfectly fine and must not be flagged.

    3. LENGTH CUE:
    Flag only if one option is massively longer (e.g., 3 lines vs 1 line) than the rest.

    4. WORD-STEM CUE:
    Flag only if a highly specific noun from the question stem appears in ONLY ONE answer option.

    5. NO FACT CHECKING:
    Assume all medical facts are correct.
    """

    dynamic_rules = ""
    if question_type == "PickS":
        dynamic_rules = """
        6. MATH RULE FOR PickS (CRITICAL):
        - PickS ALLOWS 5, 6, 7, or 8 options. NEVER say "PickS needs 4 options". 
        - The question stem MUST explicitly state the number of correct answers (e.g., "Welche 3 Aussagen...").
        - The total number of options MUST be at least TWICE the number asked for (e.g., if asking for 3, there MUST be at least 6 options). If it fails this math, flag it!
        """
    elif question_type == "Kprim":
        dynamic_rules = """
        6. MATH RULE FOR Kprim (CRITICAL):
        - Kprim MUST have EXACTLY 4 options. If it has 5 or 3, flag it with: "Bitte genau 4 Antwortoptionen bei Kprim."
        """
    else:
        dynamic_rules = """
        6. MATH RULE FOR TypA:
        - TypA usually has 4 or 5 options. Do not flag the number of options.
        """

    json_instruction = """
    OUTPUT FORMAT: Return a valid JSON object ONLY.
    {
      "_scratchpad": {
        "step_1_question_type": "Kprim, PickS or TypA",
        "step_2_number_of_options_counted": 5,
        "step_3_check_absolute_words": "Did I only flag from the 6 allowed words?"
      },
      "feedback_comments": [
        {
          "exact_quote": "Exact text from the document",
          "comment": "Short, professional explanation in German. e.g., 'Das absolute Wort (immer) ist nicht erlaubt.' or 'Bei 3 richtigen Antworten werden mindestens 6 Optionen benötigt.'"
        }
      ]
    }
    """
    return f"{base_prompt}\n{dynamic_rules}\n{json_instruction}"


def process_single_question(question_data, model_version="base"):
    """
    Processes a single question via Azure OpenAI.
    question_data should be a dict: {"id": 1, "type": "PickS", "markdown": "..."}
    model_version: "base", "v1", or "v2"
    """
    system_prompt = build_system_prompt(question_data["type"])
    
    if model_version == "v2":
        current_client = client_ft2
        current_deployment = FT2_DEPLOYMENT
    elif model_version == "v1":
        current_client = client_ft
        current_deployment = FT_DEPLOYMENT
    else:
        current_client = client
        current_deployment = DEPLOYMENT
    
    try:
        response = current_client.chat.completions.create(
            model=current_deployment,
            response_format={ "type": "json_object" },
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question_data["markdown"]}
            ]
        )
        feedback = json.loads(response.choices[0].message.content)
        return {"id": question_data["id"], "success": True, "feedback": feedback}
    except Exception as e:
        logging.error(f"Error processing question {question_data['id']}: {e}")
        return {"id": question_data["id"], "success": False, "error": str(e)}


def process_exam_in_parallel(exam_questions, model_version="base"):
    """
    Takes a list of question dictionaries and processes them concurrently.
    Populates progress.current_status with per-question status for frontend viz.
    model_version: "base", "v1", or "v2"
    """
    import progress
    import threading

    final_results = []
    total = len(exam_questions)
    completed = 0
    lock = threading.Lock()

    # Initialise question list in progress store
    progress.current_status["questions_total"] = total
    progress.current_status["questions_done"]  = 0
    progress.current_status["questions"] = [
        {"id": q["id"], "type": q["type"], "status": "pending"}
        for q in exam_questions
    ]

    def find_q_index(qid):
        for i, q in enumerate(progress.current_status["questions"]):
            if q["id"] == qid:
                return i
        return -1

    def run_with_tracking(question_data):
        nonlocal completed
        qid = question_data["id"]

        # Mark as active
        idx = find_q_index(qid)
        if idx >= 0:
            progress.current_status["questions"][idx]["status"] = "active"

        result = process_single_question(question_data, model_version=model_version)

        with lock:
            completed += 1
            status = "done" if result.get("success") else "error"
            idx = find_q_index(qid)
            if idx >= 0:
                progress.current_status["questions"][idx]["status"] = status
            progress.current_status["questions_done"]  = completed
            progress.current_status["message"]         = f"Processing exam answers ({completed}/{total})..."
            progress.current_status["progress"]        = 30 + int((completed / max(total, 1)) * 55)

        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(run_with_tracking, q): q for q in exam_questions}
        for future in concurrent.futures.as_completed(futures):
            final_results.append(future.result())

    # Sort results back to original order
    final_results = sorted(final_results, key=lambda x: x["id"])
    return final_results
