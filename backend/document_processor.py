import io
import markdownify
from docx import Document
from rules_engine import check_formatting_rules
import progress

async def process_exam_document(file_bytes: bytes, model_version: str = "base") -> bytes:
    doc = Document(io.BytesIO(file_bytes))
    
    # 1. Read exam type from header
    exam_type = "Unknown"
    for section in doc.sections:
        for header_para in section.header.paragraphs:
            if header_para.text.strip():
                exam_type = header_para.text.strip()
                break
        if exam_type != "Unknown":
            break
            
    # Fallback to first paragraph if no header
    if exam_type == "Unknown" and doc.paragraphs:
        exam_type = doc.paragraphs[0].text.strip()
    
    # 2. Extract content with inline markdown and split by "--"
    progress.current_status["message"] = "Splitting document into markdown questions..."
    progress.current_status["progress"] = 15
    progress.current_status["phase"]    = "parsing"
    
    full_text_md = ""
    for para in doc.paragraphs:
        para_md = ""
        for run in para.runs:
            if run.bold and run.text.strip():
                para_md += f"**{run.text}**"
            else:
                para_md += run.text
        full_text_md += para_md + "\n"
        
    questions = full_text_md.split("--")
    
    import asyncio
    
    # 3. Rule-based format check
    progress.current_status["message"] = "Running Python Rule-Based Formatting Engine..."
    progress.current_status["progress"] = 25
    progress.current_status["phase"]    = "parsing"
    rule_feedback = check_formatting_rules(doc, exam_type)
    
    # 4. LLM Approach for questions using parallel execution
    from llm_engine import process_exam_in_parallel
    
    import re
    exam_questions = []
    for idx, q in enumerate(questions):
        q_text = q.strip()
        if not q_text:
            continue
        
        # HARD FILTER: Skip metadata chunks with no question content
        if not re.search(r'(Typ:|Modus:)', q_text, re.IGNORECASE):
            continue
        
        # REGEX EXTRACTION: Dynamically extract the question type from this chunk
        type_match = re.search(r'Typ:\s*(\S+)', q_text, re.IGNORECASE)
        if not type_match:
            type_match = re.search(r'Modus:\s*(\S+)', q_text, re.IGNORECASE)
        
        detected_type = type_match.group(1).strip() if type_match else exam_type
        
        exam_questions.append({
            "id": idx,
            "type": detected_type,
            "markdown": q_text
        })
            
    # Run the synchronous parallel processor in a separate thread so we don't block FastAPI
    total_q = len(exam_questions)
    progress.current_status["message"] = f"Sending {total_q} questions to AI..."
    progress.current_status["progress"] = 30
    progress.current_status["phase"]    = "processing"
    
    llm_results = await asyncio.to_thread(process_exam_in_parallel, exam_questions, model_version)
    
    # Extract feedback format to match downstream Word Comment insertion logic
    progress.current_status["message"] = "Collating rules and LLM annotations..."
    progress.current_status["progress"] = 85
    progress.current_status["phase"]    = "collating"
    llm_feedback = []
    for res in llm_results:
        if res.get("success") and "feedback" in res:
            q_idx = res.get("id", -1)
            for item in res["feedback"].get("feedback_comments", []):
                llm_feedback.append({
                    "q_idx": q_idx,
                    "text": item.get("exact_quote", ""),
                    "annotation": item.get("comment", "")
                })
            
    # Normalize rules formatting feedback
    for rf in rule_feedback:
        rf["q_idx"] = -1
        
    # Combine feedback
    all_feedback = rule_feedback + llm_feedback
    
    # 5. Apply comments using native doc.add_comment()
    progress.current_status["message"] = f"Writing {len(all_feedback)} comments into document..."
    progress.current_status["progress"] = 90
    progress.current_status["phase"]    = "collating"
    
    # Pre-calculate paragraph chunks per question index to scope searches
    paragraphs_by_qidx = {}
    current_qidx = 0
    current_chunk = []
    for para in doc.paragraphs:
        if "--" in para.text:
            paragraphs_by_qidx[current_qidx] = current_chunk
            current_qidx += para.text.count("--")
            current_chunk = []
        else:
            current_chunk.append(para)
    paragraphs_by_qidx[current_qidx] = current_chunk

    seen_paras = set()
    
    for feedback_item in all_feedback:
        target_text = feedback_item["text"].strip()
        annotation = feedback_item["annotation"].strip()
        q_idx = feedback_item.get("q_idx", -1)
        added = False
        
        # Ensure we're finding non-empty text (and skip single characters to avoid reckless matching)
        if not target_text or len(target_text) < 2:
            continue
            
        search_paras = doc.paragraphs
        if q_idx != -1 and q_idx in paragraphs_by_qidx:
            search_paras = paragraphs_by_qidx[q_idx]
            
        for para in search_paras:
            if target_text in para.text:
                if para.runs:
                    try:
                        # Anchor to the first run to prevent XML corruption across complex runs
                        doc.add_comment(para.runs[0], text=annotation, author="Exam Evaluator")
                    except Exception as e:
                        print(f"Failed to add comment to paragraph: {e}")
                added = True
                break
                
        # If not found in main paragraphs, try tables
        if not added:
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            if target_text in para.text:
                                if para.runs:
                                    try:
                                        # Anchor to the first run
                                        doc.add_comment(para.runs[0], text=annotation, author="Exam Evaluator")
                                    except Exception as e:
                                        print(f"Failed to add comment to table paragraph: {e}")
                                added = True
                                break
                        if added: break
                    if added: break
                if added: break
                
    # Save modified document
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output.read()

# Make sure to import docx for the fallback RGBColor
import docx
