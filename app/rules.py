"""
Rule-based prechecks that run before LLM analysis.

These are deterministic, fast, and don't cost API credits.
Conservative by design - when in doubt, flag for human review.
"""

import re
from typing import List, Optional
from app.models import Issue


def check_pr_size(diff: str, threshold: int = 500) -> Optional[Issue]:
    """Flag large PRs that should consider being split."""
    lines_changed = len([line for line in diff.split('\n') if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))])
    
    if lines_changed > threshold:
        return Issue(
            type="pr_size",
            severity="medium",
            message=f"PR has {lines_changed} lines changed. Consider splitting for easier review.",
            confidence=1.0,
            action="review"
        )
    return None


def check_security_patterns(diff: str) -> List[Issue]:
    """Detect common security anti-patterns."""
    issues = []
    
    # Dangerous function patterns
    dangerous_patterns = {
        r'\beval\s*\(': ("Use of eval() detected", "high"),
        r'\bexec\s*\(': ("Use of exec() detected", "high"),
        r'\bpickle\.loads?\(': ("Use of pickle detected - consider safer alternatives", "medium"),
        r'password\s*=\s*["\'][^"\']+["\']': ("Possible hardcoded password", "high"),
        r'api[_-]?key\s*=\s*["\'][^"\']+["\']': ("Possible hardcoded API key", "high"),
        r'secret\s*=\s*["\'][^"\']+["\']': ("Possible hardcoded secret", "high"),
    }
    
    for pattern, (message, severity) in dangerous_patterns.items():
        if re.search(pattern, diff, re.IGNORECASE):
            issues.append(Issue(
                type="security",
                severity=severity,
                message=message,
                confidence=1.0,
                action="review"
            ))
    
    return issues


def check_import_quality(diff: str) -> List[Issue]:
    """Check for import-related issues."""
    issues = []
    
    # Star imports (import *)
    if re.search(r'from\s+\S+\s+import\s+\*', diff):
        issues.append(Issue(
            type="style",
            severity="low",
            message="Star import (import *) detected. Consider explicit imports.",
            confidence=0.9,
            action="review"
        ))
    
    return issues


def check_code_complexity(diff: str) -> List[Issue]:
    """Flag overly complex additions."""
    issues = []
    
    # Very long functions (>100 lines added in a single function)
    # This is a simplified heuristic
    added_lines = [line for line in diff.split('\n') if line.startswith('+') and not line.startswith('+++')]
    
    if len(added_lines) > 100:
        # Check if it's mostly in one function
        function_pattern = r'^\+\s*def\s+\w+\s*\('
        function_count = sum(1 for line in added_lines if re.match(function_pattern, line))
        
        if function_count == 1:
            issues.append(Issue(
                type="complexity",
                severity="medium",
                message="Large function detected (>100 lines). Consider breaking into smaller functions.",
                confidence=0.8,
                action="review"
            ))
    
    return issues


# Registry of all rule-based checks
RULE_REGISTRY = [
    check_pr_size,
    check_security_patterns,
    check_import_quality,
    check_code_complexity,
]


def run_all_rules(diff: str) -> List[Issue]:
    """Run all registered rule-based checks."""
    issues = []
    
    for rule_func in RULE_REGISTRY:
        result = rule_func(diff)
        if result:
            if isinstance(result, list):
                issues.extend(result)
            else:
                issues.append(result)
    
    return issues