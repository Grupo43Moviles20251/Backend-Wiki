import numpy as np
from models.analytics_models import ReportRequest, ReportResponse

def generate_report(request: ReportRequest) -> ReportResponse:
    data = np.array(request.data)

    return ReportResponse(
        mean=float(np.mean(data)),
        median=float(np.median(data)),
        std_dev=float(np.std(data))
    )