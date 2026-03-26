import json
import concurrent.futures
from openai import AzureOpenAI
import logging
import os

ENDPOINT = "https://smartexamapp.openai.azure.com/"
API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
API_VERSION = "2024-12-01-preview"
DEPLOYMENT = "gpt-4o"

client = AzureOpenAI(
    api_version=API_VERSION,
    azure_endpoint=ENDPOINT,
    api_key=API_KEY
)

def build_system_prompt(question_type):
    # 1. BASE PROMPT (Strict Role Definition)
    base_prompt = """
    You are a STRICT structural and didactic reviewer for medical multiple-choice exams. 
    
    CRITICAL CONSTRAINTS:
    1. DO NOT FACT-CHECK MEDICAL CONTENT. Assume all medical facts, numbers, and statements are medically correct. Your ONLY job is to check the format, structure, and didactic rules (cues).
    2. Write short, punchy, professional comments in German. Do NOT sound like an AI. Do not use phrases like "Es ist zu beachten, dass..." or "Gemäß den Regeln...". Just state the error directly.
    3. The correct answer(s) are enclosed in bold markdown (e.g., **B. Macrophages**). Unbolded options are distractors.
    
    UNIVERSAL DIDACTIC RULES (CUES) TO CHECK:
    - Absolute Words: "immer", "nie", "alle", "ausschließlich", "stets", "kein" are strictly forbidden.
    - Vague Words: "häufig", "gewöhnlich", "oft", "in der Regel" are forbidden.
    - Length Cue: Flag if the correct answer is noticeably longer/shorter or much more detailed than the distractors.
    - Word-Stem Cue: Flag if a prominent word from the question stem is repeated ONLY in the correct answer.
    - Grammar: Double negations are forbidden.
    - Opposites: If two distractors are exact logical opposites, flag it.
    """

    # 2. DYNAMIC RULES (Enforcing the Math)
    dynamic_rules = ""
    if question_type == "PickS":
        dynamic_rules = """
        SPECIFIC RULES (Type: PickS):
        YOU MUST COUNT THE OPTIONS. This is your highest priority:
        1. The question stem MUST explicitly state the EXACT number of correct answers (e.g., "3 Antworten treffen zu"). Flag if missing.
        2. Count the correct (bold) answers. Count the TOTAL answer options. There MUST be at least TWICE as many total options as correct answers (e.g., 3 correct means MINIMUM 6 total options). Maximum is 8 options. If this math fails, flag it immediately!
        """
    elif question_type == "Kprim":
        dynamic_rules = """
        SPECIFIC RULES (Type: Kprim):
        YOU MUST COUNT THE OPTIONS. This is your highest priority:
        1. There MUST be EXACTLY 4 answer options (A, B, C, D). If there are 5 or 3, you MUST flag it!
        2. The question stem must be neutral. No singular/plural hints (e.g., do not ask "Welche Diagnose...").
        """
    elif question_type == "TypA" or question_type == "TypA_neg":
        dynamic_rules = """
        SPECIFIC RULES (Type: TypA):
        - Usually has 3 to 5 options. 
        - Combinations (e.g., "A and C are correct") are absolutely forbidden.
        - If negative (TypA_neg), the negation (e.g., "nicht", "außer") must be visually emphasized.
        """

    # 3. JSON ENFORCEMENT & GRANULARITY
    json_instruction = """
    OUTPUT FORMAT: Return a valid JSON object ONLY. Do not modify the original text.
    {
      "feedback_comments": [
        {
          "exact_quote": "Extract the exact word, short phrase, or full sentence that contains the error. It MUST be an exact string match from the provided text.",
          "comment": "Short, direct, professional explanation of the structural/didactic error in German. Max 1-2 sentences. NO medical fact-checking."
        }
      ],
      "general_feedback": "Short general feedback on the structure in German."
    }
    """
    return f"{base_prompt}\n{dynamic_rules}\n{json_instruction}"


def process_single_question(question_data):
    """
    Processes a single question via Azure OpenAI.
    question_data should be a dict: {"id": 1, "type": "PickS", "markdown": "..."}
    """
    system_prompt = build_system_prompt(question_data["type"])
    
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            response_format={ "type": "json_object" },
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


def process_exam_in_parallel(exam_questions):
    """
    Takes a list of question dictionaries and processes them concurrently.
    """
    import progress
    final_results = []
    total = len(exam_questions)
    completed = 0
    
    # max_workers=10 means 10 API calls run at the exact same time
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Map the function to all questions
        future_to_question = {executor.submit(process_single_question, q): q for q in exam_questions}
        
        for future in concurrent.futures.as_completed(future_to_question):
            result = future.result()
            final_results.append(result)
            completed += 1
            progress.current_status["message"] = f"Processing exam answers ({completed}/{total})..."
            progress.current_status["progress"] = 30 + int((completed / max(total, 1)) * 55)
            
    # Sort results back to original order based on ID
    final_results = sorted(final_results, key=lambda x: x["id"])
    return final_results
