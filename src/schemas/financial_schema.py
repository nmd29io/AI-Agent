from pydantic import BaseModel, Field
from typing import List

class FinancialAnalysisSchema(BaseModel):
    de_ratio: float = Field(description="Hệ số Nợ / Vốn chủ sở hữu hiện tại (D/E)")
    pro_forma_de: float = Field(default=0.0, description="Hệ số D/E dự phóng sau khi giải ngân khoản vay")
    max_safe_limit: float = Field(default=0.0, description="Hạn mức cấp thêm an toàn tối đa theo VCSH")
    dscr: float = Field(description="Hệ số khả năng trả nợ (DSCR)")
    de_benchmark: float = Field(default=2.5, description="Ngưỡng an toàn tối đa cho D/E")
    dscr_benchmark: float = Field(default=1.2, description="Ngưỡng an toàn tối thiểu cho DSCR")
    is_de_safe: bool = Field(description="D/E có đạt chuẩn an toàn không")
    is_dscr_safe: bool = Field(description="DSCR có đạt chuẩn an toàn không")
    is_financial_healthy: bool = Field(description="Đánh giá chung về sức khỏe tài chính")
    warning_notes: List[str] = Field(default_factory=list, description="Các cảnh báo rủi ro tài chính")
    equity: float = Field(default=0.0, description="Vốn chủ sở hữu")
    total_liabilities: float = Field(default=0.0, description="Tổng nợ phải trả")
    ebitda: float = Field(default=0.0, description="EBITDA")
    annual_debt_service: float = Field(default=0.0, description="Nghĩa vụ nợ hàng năm")