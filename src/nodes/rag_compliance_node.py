import json
import os
from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from src.schemas.underwriting_state import UnderwritingState
from src.schemas.legal_schema import LegalComplianceSchema

class RagLegalEngine:
    """Engine hỗ trợ tra cứu Vector/Keyword quy định pháp lý Ngân hàng."""
    def __init__(self, regulations_path: str = "data/banking_regulations.json"):
        self.regulations_path = regulations_path
        self.regulations = self._load_regulations()

    def _load_regulations(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.regulations_path):
            return []
        with open(self.regulations_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def check_compliance(self, loan_purpose: str) -> LegalComplianceSchema:
        purpose_lower = loan_purpose.lower()
        violations = []
        warnings = []
        cited_articles = []

        for reg in self.regulations:
            # Kiểm tra xem từ khóa luật có xuất hiện trong Mục đích vay không
            matched_keywords = [kw for kw in reg["keywords"] if kw in purpose_lower]
            if matched_keywords:
                article_info = f"{reg['article']} ({reg['description']})"
                cited_articles.append(reg["article"])

                if reg["category"] == "CẤM CHO VAY":
                    violations.append(
                        f"🚫 VI PHẠM ĐIỀU CẤM: Mục đích vay liên quan đến '{', '.join(matched_keywords)}'. Căn cứ: {article_info}"
                    )
                elif reg["category"] == "CẢNH BÁO RỦI RO":
                    warnings.append(
                        f"⚠️ CẢNH BÁO KIỂM SOÁT: Mục đích vay liên quan đến '{', '.join(matched_keywords)}'. Căn cứ: {article_info}"
                    )

        is_compliant = len(violations) == 0
        has_warnings = len(warnings) > 0

        return LegalComplianceSchema(
            is_compliant=is_compliant,
            has_warnings=has_warnings,
            violations=violations,
            warnings=warnings,
            cited_articles=cited_articles
        )


async def rag_compliance_node(state: UnderwritingState) -> Dict[str, Any]:
    """
    Node 3: Tra cứu & Kiểm tra Tuân thủ Pháp lý (RAG Engine).
    """
    loan_purpose = state.get("loan_purpose", "").strip()
    
    # Khởi tạo RAG Engine
    engine = RagLegalEngine()
    legal_result = engine.check_compliance(loan_purpose)

    # Tạo Message hiển thị trên giao diện
    if not legal_result.is_compliant:
        status_icon = "🔴"
        summary_text = "PHÁT HIỆN VI PHẠM QUY ĐỊNH PHÁP LÝ NHNN"
    elif legal_result.has_warnings:
        status_icon = "🟡"
        summary_text = "CÓ CẢNH BÁO RỦI RO PHÁP LÝ CẦN KIỂM SOÁT"
    else:
        status_icon = "🟢"
        summary_text = "TUÂN THỦ HOÀN TOÀN QUY ĐỊNH PHÁP LÝ"

    status_msg = f"⚖️ **[RAG Compliance Node]:** Kết quả tra cứu Pháp lý (Thông tư 39/NHNN)\n"
    status_msg += f"- **Trạng thái:** {status_icon} **{summary_text}**\n"
    status_msg += f"- **Mục đích vay kiểm tra:** *\"{loan_purpose}\"*\n"

    if legal_result.violations:
        status_msg += "\n**Chi tiết Vi phạm:**\n" + "\n".join(legal_result.violations)
    if legal_result.warnings:
        status_msg += "\n**Chi tiết Cảnh báo:**\n" + "\n".join(legal_result.warnings)
    if not legal_result.violations and not legal_result.warnings:
        status_msg += "- **Đánh giá:** Nhu cầu vốn hợp lệ, không vi phạm các điều cấm cho vay theo Thông tư 39."

    completed = state.get("completed_steps", []) + ["node_rag_compliance"]
    return {
        "legal_compliance": legal_result.model_dump(),
        "completed_steps": completed,
        "messages": [AIMessage(content=status_msg)]
    }