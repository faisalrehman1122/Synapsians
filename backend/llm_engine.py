import json
import concurrent.futures
from openai import AzureOpenAI
import logging
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

ENDPOINT = "https://smartexamapp.openai.azure.com/"
API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
API_VERSION = "2025-01-01-preview"
DEPLOYMENT = "gpt-4o-2024-08-06-exam-linter-v1"

def set_model_choice(model_name: str):
    global DEPLOYMENT
    if model_name == "base":
        DEPLOYMENT = "gpt-4o"
    else:
        DEPLOYMENT = "gpt-4o-2024-08-06-exam-linter-v1"

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
    You are an elite, strictly algorithmic structural checker for medical exams. 
    You MUST NOT evaluate grammar, medical facts, or semantics. 
    DO NOT check for "Length Cues" (do not flag options for being too long or short).

    RULE 1: ABSOLUTE WORDS (STRICT 6-WORD WHITELIST)
    - You may ONLY flag these exact words (and their declensions like "allen", "keinen"): "immer", "nie", "alle", "ausschließlich", "stets", "kein".
    - WHOLE WORD MATCH ONLY: DO NOT flag "allein", "alleine", "ausschließen", or "ausgeschlossen".
    - EXCEPTION: If the exact absolute word appears in EVERY SINGLE answer option of a question, it is NOT a cue. DO NOT flag it.
    - SILENT REJECTION (CRITICAL): If you find a word that sounds absolute (like "sämtliche", "grundsätzlich", "zwingend", "leicht") but is NOT on the 6-word list, IGNORE IT COMPLETELY. DO NOT generate a comment saying you ignored it. ONLY output actual errors in the final JSON array.
    """

    dynamic_rules = ""
    if question_type == "PickS":
        dynamic_rules = """
        RULE 2: MATH RULE FOR PickS (CRITICAL)
        - Determine the number of correct answers (N). Find N by reading the question stem (e.g., "Welche DREI Aussagen...") OR by counting how many options are formatted in **bold** markdown in the provided text.
        - If you CANNOT find N, SKIP the math check. DO NOT flag the missing number.
        - If you CAN find N: Calculate the minimum required options M = N * 2.
        - Count the actual answer options provided (X).
        - If X < M, you MUST FLAG IT with the comment: "Bei [N] richtigen Antworten werden mindestens [M] Optionen benötigt. Hier sind nur [X]."
        """
    elif question_type == "Kprim":
        dynamic_rules = """
        RULE 2: MATH RULE FOR Kprim (CRITICAL)
        - Kprim MUST have EXACTLY 4 answer options (usually A, B, C, D).
        - Count the actual options. If there are 3, 5, or any number other than 4, you MUST FLAG IT with the comment: "Bitte genau 4 Antwortoptionen bei Kprim."
        """
    else:
        dynamic_rules = """
        RULE 2: MATH RULE FOR TypA
        - TypA usually has 4 or 5 options. Do not flag the number of options.
        """

    json_instruction = """
    OUTPUT FORMAT: Return a valid JSON object ONLY. Do not output markdown code blocks outside the JSON.
    {
      "_scratchpad": {
        "step_1_options": "Count the answer options present: [X]",
        "step_2_math": "Type: [Type]. N: [N or Unknown]. M (N*2): [M]. X: [X]. Math error? [Yes/No/Skipped]",
        "step_3_whitelist": "Did I find 'immer', 'nie', 'alle', 'ausschließlich', 'stets', 'kein'? [Yes/No]. If Yes, is it in ALL options? [Yes/No]. Is it 'allein' or 'ausschließen'? [Yes/No]",
        "step_4_chatty_check": "I will ONLY write comments for actual errors. I will NOT write comments about words I ignored."
      },
      "feedback_comments": [
        {
          "exact_quote": "Exact string causing the error (e.g., the absolute word, or the extra option letter like 'E')",
          "comment": "Short explanation in German. (e.g., 'Bitte genau 4 Antwortoptionen bei Kprim.' or 'Das absolute Wort (immer) ist nicht erlaubt.')"
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
        raw = response.choices[0].message.content
        feedback = json.loads(raw)
        n_comments = len(feedback.get('feedback_comments', []))
        import progress
        progress.current_status.setdefault("debug_log", []).append({
            "q": question_data["id"],
            "type": question_data["type"],
            "preview": question_data["markdown"][:120],
            "comments": n_comments,
            "scratchpad": feedback.get("_scratchpad", {}),
            "raw_preview": raw[:500]
        })
        return {"id": question_data["id"], "success": True, "feedback": feedback}
    except Exception as e:
        import progress
        progress.current_status.setdefault("debug_log", []).append({
            "q": question_data["id"],
            "type": question_data["type"],
            "preview": question_data["markdown"][:120],
            "error": f"{type(e).__name__}: {e}"
        })
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
