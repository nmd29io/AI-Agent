from typing import TypedDict, Annotated, List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# ==========================================
# 1. ENUMS & PYDANTIC SUB-SCHEMAS (STRUCTURED DATA)
# ==========================================


class CreditRecommendation(str, Enum):
    APPROVE = "ĐỒNG Ý CẤP TÍN DỤNG"
    REJECT = "TỪ CHỐI"
    MORE_INFO = "CẦN BỔ SUNG HỒ SƠ"


class DebtGroup(str, Enum):
    GROUP_1 = "Nhóm 1 - Nợ chuẩn"
    GROUP_2 = "Nhóm 2 - Nợ cần chú ý"
    GROUP_3 = "Nhóm 3 - Nợ dưới tiêu chuẩn"
    GROUP_4 = "Nhóm 4 - Nợ nghi ngờ"
    GROUP_5 = "Nhóm 5 - Nợ có khả năng mất vốn"


class CICStatusSchema(BaseModel):
    debt_group: DebtGroup = Field(..., description="Nhóm nợ hiện tại tại CIC")
    credit_score: int = Field(..., description="Điểm tín dụng CIC")
    overdue_36m_count: int = Field(0, description="Số lần phát sinh nợ quá hạn trong 36 tháng")
    total_current_debt: float = Field(..., description="Tổng dư nợ hiện tại tại tất cả TCD (VNĐ)")


class FinancialRatiosSchema(BaseModel):
    de_ratio: float = Field(..., description="Hệ số Nợ/VCSH (D/E)")
    dscr_ratio: float = Field(..., description="Hệ số Khả năng Trả nợ (DSCR)")
    roe_ratio: float = Field(..., description="Tỷ suất lợi luận trên VCSH (ROE)")
    is_safe: bool = Field(..., description="Cờ đánh giá an toàn tài chính (D/E <= 2.5 & DSCR >= 1.2)")


class LegalComplianceSchema(BaseModel):
    is_compliant: bool = Field(..., description="Trạng thái tuân thủ Thông tư 39 & VBHN 06")
    legal_warnings: List[str] = Field(default_factory=list, description="Danh sách các cảnh báo vi phạm pháp lý")
    cited_articles: List[str] = Field(default_factory=list, description="Trích dẫn điều khoản luật liên quan")


class AssessmentResultSchema(BaseModel):
    recommendation: CreditRecommendation = Field(..., description="Khuyến nghị cuối cùng của AI")
    approved_limit: float = Field(..., description="Hạn mức cấp tín dụng đề xuất (VNĐ)")
    submission_text: str = Field(..., description="Nội dung Tờ trình Thẩm định dạng Markdown")

# ==========================================
# 2. LANGGRAPH STATE SCHEMA (MAIN ENGINE STATE)
# ==========================================


class UnderwritingState(TypedDict):
    """
    State quản lý toàn bộ vòng đời (Lifecycle) của Workflow Thẩm định Tín dụng.
    """
    # Lịch sử hội thoại & tin nhắn tương tác (được nối chuỗi liên tục nhờ add_messages)
    messages: Annotated[List[BaseMessage], add_messages]

    # Bước 1: Thông tin Dữ liệu Đầu vào (Input Phase)
    company_tax_code: str                          # Mã số thuế (MST)
    loan_amount_requested: float                   # Số tiền xin vay (VNĐ)
    loan_purpose: str                              # Mục đích sử dụng vốn

    # Bước 2: Kết quả tra cứu CIC & CRM (Node 1)
    cic_status: Optional[Dict[str, Any]]           # Data dạng CICStatusSchema.model_dump()

    # Bước 3: Chỉ số Tài chính từ Python Engine (Node 2)
    financial_ratios: Optional[Dict[str, Any]]     # Data dạng FinancialRatiosSchema.model_dump()

    # Bước 4: Kiểm tra RAG Pháp lý (Node 3)
    legal_compliance: Optional[Dict[str, Any]]     # Data dạng LegalComplianceSchema.model_dump()

    # Bước 5: Kết quả Thẩm định & Tờ trình từ LLM (Node 4)
    assessment_result: Optional[Dict[str, Any]]    # Data dạng AssessmentResultSchema.model_dump()

    # Bước 6: Trạng thái Human-in-the-Loop (HITL Approval)
    is_approved_by_rm: bool                        # RM đã xác nhận phê duyệt chưa?
    rm_feedback: Optional[str]                     # Phản hồi/Ghi chú thêm của RM
