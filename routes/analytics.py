from fastapi import APIRouter, Depends
from services.analytics_service import generate_report
from models.analytics_models import ReportRequest, ReportResponse

router = APIRouter()

@router.post("/report", response_model=ReportResponse)
def generate_analytics_report(request: ReportRequest):
    return generate_report(request)