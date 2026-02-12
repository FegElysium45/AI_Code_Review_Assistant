"""
Standalone demo of AI Code Review Assistant.
Runs rule-based checks without external dependencies.

Usage: python demo.py
"""

import json
import re
from typing import List, Dict, Optional


def check_pr_size(diff: str, threshold: int = 500) -> Optional[Dict]:
    """Flag large PRs."""
    lines_changed = len([line for line in diff.split('\n') 
                        if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))])
    
    if lines_changed > threshold:
        return {
            "type": "pr_size",
            "severity": "medium",
            "message": f"PR has {lines_changed} lines changed. Consider splitting for easier review.",
            "confidence": 1.0,
            "action": "review"
        }
    return None


def check_security_patterns(diff: str) -> List[Dict]:
    """Detect security anti-patterns."""
    issues = []
    
    dangerous_patterns = {
        r'\beval\s*\(': ("Use of eval() detected - security risk", "high"),
        r'\bexec\s*\(': ("Use of exec() detected - security risk", "high"),
        r'password\s*=\s*["\'][^"\']+["\']': ("Possible hardcoded password", "high"),
        r'api[_-]?key\s*=\s*["\'][^"\']+["\']': ("Possible hardcoded API key", "high"),
        r'SECRET_KEY\s*=\s*["\']': ("Hardcoded secret key detected", "high"),
        r'hashlib\.md5': ("MD5 is cryptographically broken - use SHA256 or bcrypt", "high"),
    }
    
    for pattern, (message, severity) in dangerous_patterns.items():
        if re.search(pattern, diff, re.IGNORECASE):
            issues.append({
                "type": "security",
                "severity": severity,
                "message": message,
                "confidence": 1.0,
                "action": "review"
            })
    
    return issues


def check_import_quality(diff: str) -> List[Dict]:
    """Check imports."""
    issues = []
    
    if re.search(r'from\s+\S+\s+import\s+\*', diff):
        issues.append({
            "type": "style",
            "severity": "low",
            "message": "Star import (import *) detected. Consider explicit imports.",
            "confidence": 0.9,
            "action": "review"
        })
    
    return issues


def run_review(pr_data: Dict) -> Dict:
    """Run code review."""
    diff = pr_data["diff"]
    
    # Run all checks
    issues = []
    
    size_issue = check_pr_size(diff)
    if size_issue:
        issues.append(size_issue)
    
    issues.extend(check_security_patterns(diff))
    issues.extend(check_import_quality(diff))
    
    # Calculate summary
    severity_counts = {"low": 0, "medium": 0, "high": 0}
    for issue in issues:
        severity_counts[issue["severity"]] += 1
    
    return {
        "pr_number": pr_data["pr_number"],
        "issues": issues,
        "summary": {
            "total_issues": len(issues),
            "high_severity": severity_counts["high"],
            "medium_severity": severity_counts["medium"],
            "low_severity": severity_counts["low"],
        }
    }


def print_review(result: Dict):
    """Print review results."""
    print("\n" + "="*70)
    print(f"CODE REVIEW SUMMARY - PR #{result['pr_number']}")
    print("="*70)
    
    summary = result["summary"]
    print(f"\nTotal Issues: {summary['total_issues']}")
    print(f"  High Severity:   {summary['high_severity']}")
    print(f"  Medium Severity: {summary['medium_severity']}")
    print(f"  Low Severity:    {summary['low_severity']}")
    
    if result["issues"]:
        print("\n" + "-"*70)
        print("ISSUES FOUND:")
        print("-"*70)
        
        for i, issue in enumerate(result["issues"], 1):
            severity_icon = "🔴" if issue["severity"] == "high" else "🟡" if issue["severity"] == "medium" else "🟢"
            print(f"\n{i}. {severity_icon} [{issue['severity'].upper()}] {issue['type'].upper()}")
            print(f"   {issue['message']}")
            print(f"   Confidence: {issue['confidence']:.1%}")
    else:
        print("\n✅ No issues found!")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    # Load sample PR
    print("Loading sample PR...")
    with open("mock_data/sample_pr.json", "r") as f:
        pr_data = json.load(f)
    
    print(f"✓ PR #{pr_data['pr_number']}: {pr_data['title']}\n")
    
    # Run review
    print("Running code review (rule-based checks)...")
    result = run_review(pr_data)
    
    # Print results
    print_review(result)
    
    # Save output
    import os
    os.makedirs("output", exist_ok=True)
    with open("output/demo_results.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print("✓ Results saved to: output/demo_results.json\n")