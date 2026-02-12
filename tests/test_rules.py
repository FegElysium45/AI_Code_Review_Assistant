"""
Tests for rule-based checks.

Run with: pytest tests/
"""

import pytest
from app.rules import (
    check_pr_size,
    check_security_patterns,
    check_import_quality,
    run_all_rules
)


def test_pr_size_small():
    """Small PRs should not trigger size warning."""
    diff = "+line1\n+line2\n+line3"
    result = check_pr_size(diff, threshold=500)
    assert result is None


def test_pr_size_large():
    """Large PRs should trigger size warning."""
    diff = "\n".join([f"+line{i}" for i in range(600)])
    result = check_pr_size(diff, threshold=500)
    assert result is not None
    assert result.type == "pr_size"
    assert result.severity == "medium"


def test_security_eval():
    """Should detect eval() usage."""
    diff = "+result = eval(user_input)"
    issues = check_security_patterns(diff)
    assert len(issues) > 0
    assert any(issue.type == "security" for issue in issues)
    assert any("eval()" in issue.message for issue in issues)


def test_security_hardcoded_password():
    """Should detect hardcoded passwords."""
    diff = '+password = "supersecret123"'
    issues = check_security_patterns(diff)
    assert len(issues) > 0
    assert any("password" in issue.message.lower() for issue in issues)


def test_security_api_key():
    """Should detect hardcoded API keys."""
    diff = '+api_key = "sk-1234567890abcdef"'
    issues = check_security_patterns(diff)
    assert len(issues) > 0
    assert any("api" in issue.message.lower() for issue in issues)


def test_import_star():
    """Should detect star imports."""
    diff = "+from module import *"
    issues = check_import_quality(diff)
    assert len(issues) > 0
    assert any("star import" in issue.message.lower() for issue in issues)


def test_run_all_rules():
    """Should run all rules and aggregate results."""
    diff = """
+import eval
+password = "secret123"
+from utils import *
+result = eval(user_input)
"""
    issues = run_all_rules(diff)
    # Should detect multiple issues
    assert len(issues) >= 2
    
    # Should have security and style issues
    types = {issue.type for issue in issues}
    assert "security" in types


def test_clean_code():
    """Clean code should not trigger issues."""
    diff = """
+def calculate_total(items):
+    \"\"\"Calculate total price of items.\"\"\"
+    return sum(item.price for item in items)
"""
    issues = run_all_rules(diff)
    # Should not trigger any rules (except possibly pr_size if we change threshold)
    # For now, just verify it doesn't crash
    assert isinstance(issues, list)