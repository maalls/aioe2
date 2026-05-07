from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    index: int
    start: float = 0.0
    end: float = 0.0
    speaker: str = ""
    text: str = ""


class QualityFlag(BaseModel):
    segment_id: int
    risk_score: float
    severity: str
    reason: str
    evidence: str
    context_window: list[int] = Field(default_factory=list)
    suggested_action: str = "review-human"


class QualityStats(BaseModel):
    total_segments: int = 0
    flagged_segments: int = 0
    high_risk_segments: int = 0


class TranscriptQualityReport(BaseModel):
    global_score: float = 0.0
    summary: str = ""
    stats: QualityStats = Field(default_factory=QualityStats)
    flags: list[QualityFlag] = Field(default_factory=list)
