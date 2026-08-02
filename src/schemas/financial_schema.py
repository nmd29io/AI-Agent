from pydantic import BaseModel, Field

class FinancialAnalysisSchema(BaseModel):
    de_ratio: float = Field(description="Hệ số Nợ / Vốn chủ sở hữu (D/E)")
    dscr: float = Field(description="Hệ số khả năng trả nợ (DSCR)")
    de_benchmark: float = Field(default=2.5, description="Ngưỡng an toàn tối đa cho D/E")
    dscr_benchmark: float = Field(default=1.2, description="Ngưỡng an toàn tối thiểu cho DSCR")
    is_de_safe: bool = Field(description="D/E có đạt chuẩn an toàn không")
    is_dscr_safe: bool = Field(description="DSCR có đạt chuẩn an toàn không")
    is_financial_healthy: bool = Field(description="Đánh giá chung về sức khỏe tài chính")
    warning_notes: list[str] = Field(default_factory=list, description="Các cảnh báo rủi ro tài chính")