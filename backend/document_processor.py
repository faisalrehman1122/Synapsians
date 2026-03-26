import io
import markdownify
from docx import Document
from rules_engine import check_formatting_rules
import progress

async def process_exam_document(file_bytes: bytes) -> bytes:
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
    
    # 2. Extract content and split by "--"
    progress.current_status["message"] = "Splitting document into markdown questions..."
    progress.current_status["progress"] = 15
    full_text = "\n".join([p.text for p in doc.paragraphs])
    markdown_content = markdownify.markdownify(full_text)
    questions = full_text.split("--")
    
    import asyncio
    
    # 3. Rule-based format check
    progress.current_status["message"] = "Running Python Rule-Based Formatting Engine..."
    progress.current_status["progress"] = 25
    rule_feedback = check_formatting_rules(doc, exam_type)
    
    # 4. LLM Approach for questions using parallel execution
    from llm_engine import process_exam_in_parallel
    
    exam_questions = []
    for idx, q in enumerate(questions):
        if q.strip():
            exam_questions.append({
                "id": idx,
                "type": exam_type,
                "markdown": q.strip()
            })
            
    # Run the synchronous parallel processor in a separate thread so we don't block FastAPI
    total_q = len(exam_questions)
    progress.current_status["message"] = f"Initializing ThreadPool for {total_q} questions..."
    progress.current_status["progress"] = 30
    
    llm_results = await asyncio.to_thread(process_exam_in_parallel, exam_questions)
    
    # Extract feedback format to match downstream Word Comment insertion logic
    progress.current_status["message"] = "Collating rules and LLM annotations..."
    progress.current_status["progress"] = 85
    llm_feedback = []
    for res in llm_results:
        if res.get("success") and "feedback" in res:
            for item in res["feedback"].get("feedback_comments", []):
                llm_feedback.append({
                    "text": item.get("exact_quote", ""),
                    "annotation": item.get("comment", "")
                })
            
    # Combine feedback
    all_feedback = rule_feedback + llm_feedback
    
    # 5. Apply comments using native doc.add_comment()
    progress.current_status["message"] = f"Anchoring {len(all_feedback)} MS Word Comments directly into the XML..."
    progress.current_status["progress"] = 90
    
    seen_anchors = set()
    
    for feedback_item in all_feedback:
        target_text = feedback_item["text"].strip()
        annotation = feedback_item["annotation"].strip()
        added = False
        
        # Ensure we're finding non-empty text (and skip single characters to avoid reckless matching)
        if not target_text or len(target_text) < 2:
            continue
            
        for para in doc.paragraphs:
            if target_text in para.text:
                anchor_key = (id(para), annotation)
                if anchor_key in seen_anchors:
                    continue # Skip if this exact annotation was already appended to this paragraph!
                    
                if para.runs:
                    try:
                        # Anchor to the first run to prevent XML corruption across complex runs
                        doc.add_comment(para.runs[0], text=annotation, author="Exam Evaluator")
                        seen_anchors.add(anchor_key)
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
                                anchor_key = (id(para), annotation)
                                if anchor_key in seen_anchors:
                                    continue
                                    
                                if para.runs:
                                    try:
                                        # Anchor to the first run
                                        doc.add_comment(para.runs[0], text=annotation, author="Exam Evaluator")
                                        seen_anchors.add(anchor_key)
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
