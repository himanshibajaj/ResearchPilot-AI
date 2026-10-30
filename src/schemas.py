from typing import Literal
from pydantic import BaseModel, Field


class Finding(BaseModel):
    claim: str
    source_ids: list[str] = Field(min_length=1)  # bina source ke claim allowed nahi


class FinalAnswer(BaseModel):
    user_question: str
    short_answer: str
    key_findings: list[Finding]
    confidence: Literal["high", "medium", "low"]
    confidence_reason: str
    limitations_and_assumptions: list[str]
    next_steps: list[str]
    
class Plan(BaseModel):
    sub_questions: list[str] = Field(min_length=1, max_length=4)
    search_queries: list[str] = Field(min_length=1, max_length=4)
    assumptions: list[str]
    
class ClaimCheck(BaseModel):
    claim_index: int
    supported: bool
    note: str

class JudgeResult(BaseModel):
    checks: list[ClaimCheck]