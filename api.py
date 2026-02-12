# api.py
"""
FastAPI wrapper for AI Code Review Assistant.
Exposes rule-based checks as a REST API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import re

app = FastAPI(
    title="AI Code Review Assistant",
    description="Conservative, read-only code review for Python PRs",
    version="1.0.0"
)

# ── Inline rule-based checks (no LLM, no API keys needed) ──────────────────

def check_security_patterns(diff: str):
    issues = []
    patterns = {
        r'\beval\s*\(':        ("Use of eval() detected - security risk", "high"),
        r'\bexec\s*\(':        ("Use of exec() detected - security risk", "high"),
        r'password\s*=\s*["\'][^"\']+["\']': ("Possible hardcoded password", "high"),
        r'api[_-]?key\s*=\s*["\'][^"\']+["\']': ("Possible hardcoded API key", "high"),
        r'SECRET_KEY\s*=\s*["\']': ("Hardcoded secret key detected", "high"),
        r'hashlib\.md5':       ("MD5 is broken - use SHA256 or bcrypt", "high"),
        r'\bpickle\.loads?\(': ("pickle.load() is unsafe - use safer alternatives", "medium"),
    }
    for pattern, (message, severity) in patterns.items():
        if re.search(pattern, diff, re.IGNORECASE):
            issues.append({"type": "security", "severity": severity,
                           "message": message, "confidence": 1.0, "action": "review"})
    return issues


def check_pr_size(diff: str, threshold: int = 500):
    lines = [l for l in diff.split('\n')
             if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))]
    if len(lines) > threshold:
        return {"type": "pr_size", "severity": "medium",
                "message": f"PR has {len(lines)} lines changed. Consider splitting.",
                "confidence": 1.0, "action": "review"}
    return None


def check_import_quality(diff: str):
    issues = []
    if re.search(r'from\s+\S+\s+import\s+\*', diff):
        issues.append({"type": "style", "severity": "low",
                       "message": "Star import (import *) detected. Use explicit imports.",
                       "confidence": 0.9, "action": "review"})
    return issues


def run_review(diff: str):
    issues = []
    size = check_pr_size(diff)
    if size:
        issues.append(size)
    issues.extend(check_security_patterns(diff))
    issues.extend(check_import_quality(diff))
    counts = {"low": 0, "medium": 0, "high": 0}
    for i in issues:
        counts[i["severity"]] += 1
    return issues, counts

# ── Request / Response models ───────────────────────────────────────────────

class ReviewRequest(BaseModel):
    pr_number: int
    title: str
    description: str = ""
    diff: str

class HealthResponse(BaseModel):
    status: str
    version: str
    mode: str

# ── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/", response_model=HealthResponse)
def root():
    return {"status": "ok", "version": "1.0.0", "mode": "rule-based"}


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "version": "1.0.0", "mode": "rule-based"}


@app.post("/review")
def review(request: ReviewRequest):
    if not request.diff:
        raise HTTPException(status_code=400, detail="diff is required")

    issues, counts = run_review(request.diff)

    return JSONResponse({
        "pr_number": request.pr_number,
        "title":     request.title,
        "issues":    issues,
        "summary": {
            "total_issues":    len(issues),
            "high_severity":   counts["high"],
            "medium_severity": counts["medium"],
            "low_severity":    counts["low"],
            "llm_used":        False,
            "mode":            "rule-based"
        }
    })


@app.get("/demo")
def demo():
    """Returns a pre-reviewed sample PR so Wave can see it live."""
    sample_diff = (
        '+SECRET_KEY = "hardcoded-key-123"\n'
        '+result = eval(user_input)\n'
        '+import hashlib\n'
        '+hashlib.md5(password.encode()).hexdigest()\n'
        '+from utils import *\n'
    )
    issues, counts = run_review(sample_diff)
    return JSONResponse({
        "pr_number": 9999,
        "title":     "Demo: Auth endpoint with intentional security issues",
        "issues":    issues,
        "summary": {
            "total_issues":    len(issues),
            "high_severity":   counts["high"],
            "medium_severity": counts["medium"],
            "low_severity":    counts["low"],
            "llm_used":        False,
            "mode":            "rule-based (LLM integration ready)"
        }
    })
```

---

## **Step 2: Add these two files to your repo root**
```
# Procfile
web: uvicorn api:app --host 0.0.0.0 --port $PORT
```
```
# runtime.txt
python-3.11.0
```

---

## **Step 3: Update requirements.txt**

Add these two lines at the top:
```
fastapi>=0.104.0
uvicorn>=0.24.0
```

Your full `requirements.txt` becomes:
```
fastapi>=0.104.0
uvicorn>=0.24.0
openai>=1.0.0
anthropic>=0.18.0
pydantic>=2.0.0
python-dotenv>=1.0.0
requests>=2.31.0
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
mypy>=1.0.0