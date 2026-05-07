from pydantic import BaseModel, Field


class QAPair(BaseModel):
    question: str
    answer: str
    questioner: str = ""
    answerer: str = ""


class Decision(BaseModel):
    decision: str
    owner: str = ""


class SubTopic(BaseModel):
    title: str
    summary: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)


class ChapterAnalysis(BaseModel):
    sub_topics: list[SubTopic] = []
    qa_pairs: list[QAPair] = []
    decisions: list[Decision] = []


class TimelineChapter(BaseModel):
    title: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    summary: str = ""
    analysis: ChapterAnalysis | None = None


class MeetingTimelineReport(BaseModel):
    source_json: str
    generated_at: str
    chapter_count: int
    chapters: list[TimelineChapter]
    warnings: list[str] = []
