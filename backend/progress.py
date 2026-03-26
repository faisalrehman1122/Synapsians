current_status = {
    "message": "Ready",
    "progress": 0,
    # Phase drives the Three.js scene on the frontend
    # Values: "idle" | "uploading" | "parsing" | "processing" | "collating" | "complete"
    "phase": "idle",
    # Questions list: populated once total is known
    # Each entry: { "id": int, "type": str, "status": "pending"|"active"|"done"|"error" }
    "questions": [],
    "questions_total": 0,
    "questions_done": 0,
}

def reset():
    current_status["message"]         = "Ready"
    current_status["progress"]        = 0
    current_status["phase"]           = "idle"
    current_status["questions"]       = []
    current_status["questions_total"] = 0
    current_status["questions_done"]  = 0
