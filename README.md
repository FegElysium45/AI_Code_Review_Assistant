# AI Code Review Assistant

**Reduce reviewer fatigue. Surface common issues early. Keep humans focused on what matters.**

A conservative, read-only code review assistant for Python pull requests. Combines rule-based checks with AI analysis to catch style issues, simple bugs, and security hints—so your senior engineers can focus on architecture and business logic.

---

## 🚀 Live Deployment

[![API Docs](https://img.shields.io/badge/API%20Docs-Live-blue?style=for-the-badge)](https://ai-code-review-assistant-gu0p.onrender.com/docs)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Try%20It-green?style=for-the-badge)](https://ai-code-review-assistant-gu0p.onrender.com/demo)

| Endpoint | URL |
|----------|-----|
| 📖 Interactive API Docs | https://ai-code-review-assistant-gu0p.onrender.com/docs |
| ⚡ Live Demo | https://ai-code-review-assistant-gu0p.onrender.com/demo |
| ❤️ Health Check | https://ai-code-review-assistant-gu0p.onrender.com/health |

> **Note:** Hosted on Render free tier — first request may take 30–60 seconds to wake up.

---

## Why This Exists

**Problem:** Engineering teams spend hours reviewing PRs for issues that could be caught automatically—formatting inconsistencies, common anti-patterns, simple security oversights.

**Solution:** This assistant runs rule-based prechecks and optional AI analysis on every PR, surfacing low-hanging fruit before human review. It never blocks PRs or auto-merges—it's advisory only.

**Impact:**
- Reduces time spent on trivial review comments
- Catches common issues before code review
- Frees senior engineers to focus on complex design decisions

Designed for containerized deployment via Docker, integrable with enterprise orchestration layers like n8n or AWS Lambda.

---

## What It Checks

### Rule-Based (Always Runs)
- PR size limits (flags PRs >500 lines for split consideration)
- Security patterns (detects `eval()`, `pickle`, hardcoded secrets patterns)
- Import quality (flags unused imports, circular dependencies)
- Basic style (excessive complexity, missing docstrings)

### AI-Powered (Optional)
- Code correctness hints (potential bugs, edge cases)
- Style consistency with existing codebase
- Security considerations beyond pattern matching
- Performance anti-patterns

**Output:** Structured JSON with issue type, severity, confidence score, and suggested action (review / ignore).

---

## Architecture

```
[PR Diff Input]
       ↓
[Rule-Based Prechecks] ← size, security patterns, imports
       ↓
[Prompt Builder] ← structured system + task prompts
       ↓
[LLM Call] ← OpenAI/Anthropic/local
       ↓
[Confidence Filter] ← threshold: 0.7+
       ↓
[Review Output] ← JSON: {type, severity, confidence, action}
```

**Design Principles:**
- Conservative: when uncertain, defer to humans
- Observable: log everything, measure false positives
- Fail-safe: errors never block PRs

---

## Quick Start

### Option 1: Live API (No Setup Required)
Hit the live demo endpoint directly:
```bash
curl https://ai-code-review-assistant-gu0p.onrender.com/demo
```

Or POST your own PR diff:
```bash
curl -X POST https://ai-code-review-assistant-gu0p.onrender.com/review \
  -H "Content-Type: application/json" \
  -d '{
    "pr_number": 42,
    "title": "Add auth endpoint",
    "diff": "+SECRET_KEY = \"hardcoded-key\"\n+result = eval(user_input)"
  }'
```

### Option 2: Run Locally
```bash
pip install -r requirements.txt
python app/main.py --pr-file mock_data/sample_pr.json
```

---

## How to Extend Rules

Rules live in `app/rules.py` as simple Python functions:
```python
def check_pr_size(diff: str) -> Optional[Issue]:
    """Flag PRs over 500 lines"""
    lines_changed = count_lines(diff)
    if lines_changed > 500:
        return Issue(
            type="pr_size",
            severity="warning",
            message=f"PR has {lines_changed} lines. Consider splitting.",
            confidence=1.0
        )
    return None
```
Add your rule, register it in `RULE_REGISTRY`, done.

---

## How to Swap LLM Providers

All LLM calls go through `app/reviewer.py`. To switch providers:

**From OpenAI to Anthropic:**
```python
# Before
response = openai.ChatCompletion.create(...)

# After
response = anthropic.Completions.create(...)
```

**From API to local model:**
```python
# Use llama.cpp, Ollama, or vLLM
response = requests.post("http://localhost:8000/v1/chat/completions", ...)
```

**Environment variables:**
```bash
export LLM_PROVIDER=openai  # or anthropic, local
export LLM_MODEL=gpt-4      # or claude-3-sonnet, llama-3-70b
export LLM_API_KEY=sk-...
```

---

## Non-Goals

This tool **will not**:
- ❌ Auto-approve or auto-merge PRs
- ❌ Write code or generate fixes
- ❌ Make architectural or business logic decisions
- ❌ Modify pull requests

It's advisory only. Humans always have final say.

---

## Production Considerations

**Observability:**
- Log all reviews (latency, confidence scores, issues found)
- Track false positive rates via human feedback
- Monitor LLM API costs per PR

**Security:**
- Read-only access to PR diffs (no write permissions)
- Secrets scanning before LLM prompt injection
- Rate limits: 10 PRs/minute, $50/month budget cap

**Failure Handling:**
- LLM timeout → skip AI, use rule-based only
- Invalid output → log, alert, continue with rules
- Never blocks PR merges

**Rollback:**
- Prompts versioned in Git
- Rule changes deployed via feature flags
- Manual override: `skip-ai-review` label on PR

---

## Sample Output

```json
{
  "pr_number": 9999,
  "title": "Demo: Auth endpoint with intentional security issues",
  "issues": [
    {
      "type": "security",
      "severity": "high",
      "message": "Use of eval() detected - security risk",
      "confidence": 1.0,
      "action": "review"
    },
    {
      "type": "security",
      "severity": "high",
      "message": "Hardcoded secret key detected",
      "confidence": 1.0,
      "action": "review"
    },
    {
      "type": "style",
      "severity": "low",
      "message": "Star import (import *) detected. Use explicit imports.",
      "confidence": 0.9,
      "action": "review"
    }
  ],
  "summary": {
    "total_issues": 4,
    "high_severity": 3,
    "low_severity": 1,
    "llm_used": false,
    "mode": "rule-based (LLM integration ready)"
  }
}
```

---

## Future Work

- Multi-language support (TypeScript, Go, Rust)
- Fine-tuned model on team's historical PR comments
- Human feedback loop (thumbs up/down on suggestions)
- Integration with Slack for review notifications
- GitHub Action for automatic PR triggering

---

## License

MIT

---

## Contributing

PRs welcome. See `CONTRIBUTING.md` for guidelines.
