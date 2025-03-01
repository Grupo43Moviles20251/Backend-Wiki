from pydantic import BaseModel
from typing import List

class ReportRequest(BaseModel):
    data: List[float]

class ReportResponse(BaseModel):
    mean: float
    median: float
    std_dev: float