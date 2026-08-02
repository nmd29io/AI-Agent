from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class CreditDecisionEnum(str, Enum):
    APPROVE = "ĐỒNG Ý CẤP TÍN DỤNG"
    REJECT = "TỪ CHỐI CẤP TÍN DỤNG"
    MORE_INFO = "CẦN BỔ SUNG HỒ SƠ"

class UnderwritingAssessmentSchema(BaseModel):
    decision: CreditDecisionEnum = Field(description="Quyết định/Khuyến nghị cuối cùng về khoản vay")
    recommended_credit_limit: float = Field(description="Hạn mức cấp tín dụng đề xuất tối đa (VNĐ)")
    risk_level: str = Field(description="Mức độ rủi ro của khoản vay: Thấp, Trung bình, Cao, Rất cao")
    key_strengths: List[str] = Field(description="Các điểm mạnh của hồ sơ (về tài chính, CIC, tư cách pháp lý)")
    key_risks: List[str] = Field(description="Các yếu tố rủi ro chính cần lưu ý")
    submission_report_markdown: str = Field(description="Nội dung Tờ trình Thẩm định Tín dụng chi tiết dạng Markdown chuẩn nghiệp vụ")