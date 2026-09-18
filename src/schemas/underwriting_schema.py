from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from enum import Enum

class CreditDecisionEnum(str, Enum):
    APPROVE = "ĐỒNG Ý CẤP TÍN DỤNG"
    REJECT = "TỪ CHỐI CẤP TÍN DỤNG"
    MORE_INFO = "CẦN BỔ SUNG HỒ SƠ"

class LLMAssessmentOutput(BaseModel):
    decision: CreditDecisionEnum = Field(description="Quyết định/Khuyến nghị cuối cùng: APPROVE, REJECT, hoặc MORE_INFO")
    recommended_credit_limit: float = Field(description="Hạn mức cấp tín dụng đề xuất tối đa (VNĐ)")
    risk_level: str = Field(description="Mức độ rủi ro của khoản vay: Thấp, Trung bình, Cao, Rất cao")
    summary_notes: str = Field(description="Tóm tắt lý do và căn cứ cốt lõi cho phán quyết tín dụng")
    key_strengths: List[str] = Field(default_factory=list, description="Các điểm mạnh của hồ sơ")
    key_risks: List[str] = Field(default_factory=list, description="Các yếu tố rủi ro chính cần lưu ý")
    conditions_precedent: List[str] = Field(default_factory=list, description="Điều kiện tiên quyết trước khi giải ngân")
    post_disbursement_monitoring: List[str] = Field(default_factory=list, description="Điều kiện quản lý và giám sát sau giải ngân")

class UnderwritingAssessmentSchema(LLMAssessmentOutput):
    submission_report_markdown: str = Field(default="", description="Nội dung Tờ trình Thẩm định Tín dụng chi tiết dạng Markdown chuẩn nghiệp vụ ngân hàng 7 phần")
    markdown_report: Optional[str] = Field(default=None, description="Đồng bộ với submission_report_markdown")

    @model_validator(mode="after")
    def sync_markdown_fields(self):
        if not self.submission_report_markdown and self.markdown_report:
            self.submission_report_markdown = self.markdown_report
        elif not self.markdown_report and self.submission_report_markdown:
            self.markdown_report = self.submission_report_markdown
        return self