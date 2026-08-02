from pydantic import BaseModel, Field
from typing import List

class LegalComplianceSchema(BaseModel):
    is_compliant: bool = Field(description="Trạng thái tuân thủ pháp lý (True nếu hợp lệ, False nếu vi phạm/rủi ro)")
    has_warnings: bool = Field(description="Có cảnh báo rủi ro pháp lý cần lưu ý hay không")
    violations: List[str] = Field(default_factory=list, description="Danh sách các vi phạm điều cấm (nếu có)")
    warnings: List[str] = Field(default_factory=list, description="Danh sách các cảnh báo rủi ro kiểm soát")
    cited_articles: List[str] = Field(default_factory=list, description="Trích dẫn các điều khoản luật liên quan (Ví dụ: Điều 8 Thông tư 39)")