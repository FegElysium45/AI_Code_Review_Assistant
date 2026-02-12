"""
Main entry point for AI code review assistant.

Usage:
    python app/main.py --pr-file mock_data/sample_pr.json
    python app/main.py --pr-file sample.json --no-llm
    python app/main.py --pr-file sample.json --provider anthropic --model claude-3-sonnet-20240229
"""

import argparse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

from app.models import PRDiff
from app.reviewer import review_pr


def load_pr_from_file(filepath: str) -> PRDiff:
    """Load PR data from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return PRDiff(**data)


def save_output(output, filepath: str):
    """Save review output to JSON file."""
    output_dir = Path(filepath).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(output.model_dump(), f, indent=2)
    
    print(f"\n✓ Review output saved to: {filepath}")


def print_summary(output):
    """Print human-readable summary to console."""
    print("\n" + "="*60)
    print(f"CODE REVIEW SUMMARY - PR #{output.pr_number}")
    print("="*60)
    
    summary = output.summary
    print(f"\nTotal Issues: {summary.total_issues}")
    print(f"  High Severity: {summary.high_severity}")
    print(f"  Medium Severity: {summary.medium_severity}")
    print(f"  Low Severity: {summary.low_severity}")
    print(f"\nReview Time: {summary.review_time_seconds}s")
    print(f"LLM Used: {'Yes' if summary.llm_used else 'No (rule-based only)'}")
    if summary.model_name:
        print(f"Model: {summary.model_name}")
    
    if output.issues:
        print("\n" + "-"*60)
        print("ISSUES FOUND:")
        print("-"*60)
        
        for i, issue in enumerate(output.issues, 1):
            print(f"\n{i}. [{issue.severity.upper()}] {issue.type}")
            print(f"   {issue.message}")
            print(f"   Confidence: {issue.confidence:.2f}")
            if issue.file_path:
                print(f"   File: {issue.file_path}")
            if issue.line_number:
                print(f"   Line: {issue.line_number}")
    else:
        print("\n✓ No issues found!")
    
    print("\n" + "="*60)


def main():
    """Main CLI entry point."""
    load_dotenv()  # Load environment variables from .env file
    
    parser = argparse.ArgumentParser(
        description="AI Code Review Assistant - Conservative, read-only PR analysis"
    )
    parser.add_argument(
        "--pr-file",
        required=True,
        help="Path to PR JSON file"
    )
    parser.add_argument(
        "--output",
        default="output/review_results.json",
        help="Output file path (default: output/review_results.json)"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM analysis, use rule-based checks only"
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "local"],
        default="openai",
        help="LLM provider (default: openai)"
    )
    parser.add_argument(
        "--model",
        default="gpt-4",
        help="Model name (default: gpt-4)"
    )
    
    args = parser.parse_args()
    
    try:
        # Load PR data
        print(f"Loading PR from: {args.pr_file}")
        pr_diff = load_pr_from_file(args.pr_file)
        print(f"✓ Loaded PR #{pr_diff.pr_number}: {pr_diff.title}")
        
        # Run review
        print(f"\nRunning review (LLM: {'disabled' if args.no_llm else args.provider + '/' + args.model})...")
        output = review_pr(
            pr_diff,
            use_llm=not args.no_llm,
            llm_provider=args.provider,
            llm_model=args.model,
        )
        
        # Print summary
        print_summary(output)
        
        # Save output
        save_output(output, args.output)
        
        # Exit code based on high-severity issues (optional)
        # Could be used in CI to fail builds
        if output.summary.high_severity > 0:
            print(f"\n⚠ Warning: {output.summary.high_severity} high-severity issue(s) found")
            # Note: We don't exit with error code because this is advisory only
            # In production, you might want: sys.exit(1)
        
        return 0
    
    except FileNotFoundError:
        print(f"Error: PR file not found: {args.pr_file}", file=sys.stderr)
        return 1
    
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())