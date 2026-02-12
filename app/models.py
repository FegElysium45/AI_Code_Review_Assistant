"""
Data models for code review assistant.
Using Pydantic for validation and type safety.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class Issue(BaseModel):
    """Single review issue found in PR."""
    
    type: str = Field(..., description="Issue category: security, style, correctness, performance")
    severity: Literal["low", "medium", "high"] = Field(..., description="Issue severity")
    message: str = Field(..., description="Human-readable explanation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    action: Literal["review", "ignore"] = Field(..., description="Suggested action")
    line_number: Optional[int] = Field(None, description="Line number if applicable")
    file_path: Optional[str] = Field(None, description="File path if applicable")


class PRDiff(BaseModel):
    """Pull request diff input."""
    
    pr_number: int
    title: str
    description: str
    author: str
    files_changed: List[str]
    diff: str = Field(..., description="Full diff content")
    commit_message: str


class ReviewSummary(BaseModel):
    """Summary of review results."""
    
    total_issues: int
    high_severity: int
    medium_severity: int
    low_severity: int
    review_time_seconds: float
    llm_used: bool
    model_name: Optional[str] = None


class ReviewOutput(BaseModel):
    """Complete review output."""
    
    pr_number: int
    issues: List[Issue]
    summary: ReviewSummary
    metadata: dict = Field(default_factory=dict)