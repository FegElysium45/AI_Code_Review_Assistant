"""
Core reviewer module.

Orchestrates rule-based checks + optional LLM analysis.
Handles failures gracefully - never blocks PRs.
"""

import os
import json
import time
import logging
from typing import List, Optional
from app.models import Issue, PRDiff, ReviewOutput, ReviewSummary
from app.rules import run_all_rules
from app.prompts import SYSTEM_PROMPT, build_task_prompt, PROMPT_VERSION

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Confidence threshold for LLM-generated issues
# Issues below this threshold are filtered out to reduce false positives
CONFIDENCE_THRESHOLD = 0.7


class ReviewerError(Exception):
    """Base exception for reviewer errors."""
    pass


class LLMTimeoutError(ReviewerError):
    """LLM call timed out."""
    pass


class LLMInvalidOutputError(ReviewerError):
    """LLM returned invalid output."""
    pass


def call_llm(pr_diff: PRDiff, provider: str = "openai", model: str = "gpt-4", timeout: int = 30) -> List[Issue]:
    """
    Call LLM for code review analysis.
    
    Failure modes:
    - Timeout → raises LLMTimeoutError
    - Invalid output → raises LLMInvalidOutputError
    - API error → raises ReviewerError
    
    Caller must handle these gracefully.
    """
    task_prompt = build_task_prompt(pr_diff.diff, pr_diff.title, pr_diff.description)
    
    try:
        if provider == "openai":
            return _call_openai(task_prompt, model, timeout)
        elif provider == "anthropic":
            return _call_anthropic(task_prompt, model, timeout)
        elif provider == "local":
            return _call_local(task_prompt, model, timeout)
        else:
            raise ReviewerError(f"Unsupported LLM provider: {provider}")
    
    except Exception as e:
        # Re-raise as ReviewerError for consistent handling
        if isinstance(e, (LLMTimeoutError, LLMInvalidOutputError, ReviewerError)):
            raise
        raise ReviewerError(f"LLM call failed: {str(e)}")


def _call_openai(task_prompt: str, model: str, timeout: int) -> List[Issue]:
    """Call OpenAI API."""
    try:
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ReviewerError("OPENAI_API_KEY not set")
        
        client = OpenAI(api_key=api_key, timeout=timeout)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": task_prompt}
            ],
            temperature=0.1,  # Low temperature for consistency
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content
        return _parse_llm_output(content)
    
    except Exception as e:
        if "timeout" in str(e).lower():
            raise LLMTimeoutError("OpenAI API timeout")
        raise ReviewerError(f"OpenAI API error: {str(e)}")


def _call_anthropic(task_prompt: str, model: str, timeout: int) -> List[Issue]:
    """
    Call Anthropic API via LangChain integration.

    Why LangChain here:
    - Unified interface: swapping to GPT-4 or a local model
      later requires zero changes to this function's callers
    - Built-in retry logic and timeout handling
    - Provider-agnostic message format (HumanMessage/SystemMessage)
    - Future-ready: adding tools, memory, or chains requires
      no architectural changes
    """
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, SystemMessage

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ReviewerError("ANTHROPIC_API_KEY not set")

        llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0.1,
            max_tokens=2000,
            timeout=timeout,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=task_prompt),
        ]

        response = llm.invoke(messages)
        return _parse_llm_output(response.content)

    except Exception as e:
        raise ReviewerError(f"Anthropic (LangChain) error: {str(e)}")




def _call_anthropic(task_prompt: str, model: str, timeout: int) -> List[Issue]:
    """
    Call Anthropic API via LangChain integration.

    Why LangChain here:
    - Unified interface: swapping to GPT-4 or a local model
      later requires zero changes to this function's callers
    - Built-in retry logic and timeout handling
    - Provider-agnostic message format (HumanMessage/SystemMessage)
    - Future-ready: adding tools, memory, or chains requires
      no architectural changes
    """
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, SystemMessage

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ReviewerError("ANTHROPIC_API_KEY not set")

        llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0.1,
            max_tokens=2000,
            timeout=timeout,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=task_prompt),
        ]

        response = llm.invoke(messages)
        return _parse_llm_output(response.content)

    except Exception as e:
        raise ReviewerError(f"Anthropic (LangChain) error: {str(e)}")






def _call_local(task_prompt: str, model: str, timeout: int) -> List[Issue]:
    """Call local LLM server (e.g., Ollama, vLLM)."""
    import requests
    
    endpoint = os.getenv("LOCAL_LLM_ENDPOINT", "http://localhost:8000/v1/chat/completions")
    
    try:
        response = requests.post(
            endpoint,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": task_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2000,
            },
            timeout=timeout
        )
        response.raise_for_status()
        
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_llm_output(content)
    
    except requests.Timeout:
        raise LLMTimeoutError("Local LLM timeout")
    except Exception as e:
        raise ReviewerError(f"Local LLM error: {str(e)}")


def _parse_llm_output(content: str) -> List[Issue]:
    """Parse LLM output into Issue objects."""
    try:
        # Strip markdown code blocks if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        issues_data = json.loads(content)
        
        if not isinstance(issues_data, list):
            raise LLMInvalidOutputError("LLM output is not a JSON array")
        
        # Validate and convert to Issue objects
        issues = []
        for item in issues_data:
            try:
                issue = Issue(**item)
                # Apply confidence threshold
                if issue.confidence >= CONFIDENCE_THRESHOLD:
                    issues.append(issue)
            except Exception as e:
                # Log but don't fail - skip invalid issues
                logger.warning(f"Skipping invalid issue: {e}")
                continue
        
        return issues
    
    except json.JSONDecodeError:
        raise LLMInvalidOutputError("LLM output is not valid JSON")
    except Exception as e:
        raise LLMInvalidOutputError(f"Failed to parse LLM output: {str(e)}")


def review_pr(
    pr_diff: PRDiff,
    use_llm: bool = True,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4",
) -> ReviewOutput:
    """
    Review a pull request.
    
    Workflow:
    1. Run rule-based checks (always)
    2. Run LLM analysis (optional, graceful degradation on failure)
    3. Combine and return results
    
    Never fails - degrades gracefully to rule-based only.
    """
    start_time = time.time()
    
    # Step 1: Rule-based checks (deterministic, always run)
    rule_issues = run_all_rules(pr_diff.diff)
    
    # Step 2: LLM analysis (optional, may fail)
    llm_issues = []
    llm_used = False
    model_name = None
    
    if use_llm:
        try:
            llm_issues = call_llm(pr_diff, provider=llm_provider, model=llm_model)
            llm_used = True
            model_name = llm_model
            logger.info(f"LLM analysis completed: {len(llm_issues)} issues found")
        
        except LLMTimeoutError:
            logger.warning("LLM timeout - continuing with rule-based checks only")
        
        except LLMInvalidOutputError as e:
            logger.warning(f"LLM invalid output - continuing with rule-based checks only: {e}")
        
        except ReviewerError as e:
            logger.warning(f"LLM error - continuing with rule-based checks only: {e}")
    
    # Step 3: Combine results
    all_issues = rule_issues + llm_issues
    
    # Compute summary
    severity_counts = {"low": 0, "medium": 0, "high": 0}
    for issue in all_issues:
        severity_counts[issue.severity] += 1
    
    summary = ReviewSummary(
        total_issues=len(all_issues),
        high_severity=severity_counts["high"],
        medium_severity=severity_counts["medium"],
        low_severity=severity_counts["low"],
        review_time_seconds=round(time.time() - start_time, 2),
        llm_used=llm_used,
        model_name=model_name,
    )
    
    return ReviewOutput(
        pr_number=pr_diff.pr_number,
        issues=all_issues,
        summary=summary,
        metadata={
            "prompt_version": PROMPT_VERSION,
            "llm_provider": llm_provider if llm_used else None,
        }
    )