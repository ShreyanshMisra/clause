from enum import Enum
from typing import Optional
from pydantic import BaseModel

class Severity(str, Enum):
    illegal = "illegal"
    high = "high"
    medium = "medium"
    favorable = "favorable"

COLOR_BY_SEVERITY = {
    Severity.illegal: "red",
    Severity.high: "orange",
    Severity.medium: "yellow",
    Severity.favorable: "green",
}

class BoundingRect(BaseModel):
    x1: float; y1: float; x2: float; y2: float
    width: float; height: float; pageNumber: int

class HighlightPosition(BaseModel):
    boundingRect: BoundingRect
    rects: list[BoundingRect]
    pageWidth: float
    pageHeight: float

class Finding(BaseModel):
    id: str
    page: int
    quoted_text: str
    category: str
    severity: Severity
    color: str
    statute_citation: Optional[str] = None
    explanation: str
    damages_estimate: Optional[float] = None
    position: Optional[HighlightPosition] = None

class Parties(BaseModel):
    landlord: str = ""
    tenant: str = ""
    property: str = ""

class Metadata(BaseModel):
    parties: Parties = Parties()
    monthlyRent: str = ""
    leaseTerm: str = ""
    securityDeposit: str = ""

class DeidentificationSummary(BaseModel):
    redactedEntities: dict[str, int] = {}
    encryptionStatus: str = "disabled"

class TopIssue(BaseModel):
    title: str
    severity: str
    amount: Optional[str] = None

class AnalysisSummary(BaseModel):
    overallRisk: str = "Low"
    issuesFound: int = 0
    estimatedRecovery: str = "$0"
    topIssues: list[TopIssue] = []

class AnalysisResult(BaseModel):
    documentId: str
    documentMetadata: Metadata = Metadata()
    deidentificationSummary: DeidentificationSummary = DeidentificationSummary()
    analysisSummary: AnalysisSummary = AnalysisSummary()
    highlights: list[Finding] = []

class JobStatus(BaseModel):
    file_id: str
    status: str  # uploaded | processing | metadata_extracted | completed | failed
    progress: int = 0
    message: str = ""
    filename: Optional[str] = None
