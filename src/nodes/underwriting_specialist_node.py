import os
from typing import Dict, Any
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.schemas.underwriting_state import UnderwritingState
from src.schemas.underwriting_schema import UnderwritingAssessmentSchema, CreditDecisionEnum


async def underwriting_specialist_node(state: UnderwritingState) -> Dict[str, Any]:
    """
    Node 4: AI Underwriting Specialist - LLM đọc dữ liệu từ các Node trước để sinh phán quyết & Tờ trình Thẩm định.
    """
    # 1. Trích xuất thông tin từ State
    tax_code = state.get("company_tax_code", "N/A")
    loan_requested = state.get("loan_amount_requested", 0.0)
    loan_purpose = state.get("loan_purpose", "N/A")

    cic_data = state.get("cic_status", {})
    financial_data = state.get("financial_ratios", {})
    legal_data = state.get("legal_compliance", {})

    # 2. Khởi tạo Gemini Model với Structured Output
    # Lưu ý: Cần thiết lập GEMINI_API_KEY trong biến môi trường (.env)
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
    )
    structured_llm = llm.with_structured_output(UnderwritingAssessmentSchema)

    # 3. Soạn Prompt thẩm định chuyên sâu
    system_prompt = f"""
Bạn là Chuyên viên Thẩm định Tín dụng Doanh nghiệp Cấp cao tại Ngân hàng.
Nhiệm vụ của bạn là phân tích toàn bộ dữ liệu hồ sơ được tổng hợp từ các hệ thống chuyên biệt và đưa ra **Tờ trình Thẩm định Tín dụng** chính xác, khách quan.

### THÔNG TIN YÊU CẦU KHOẢN VAY:
- Mã số thuế: {tax_code}
- Số tiền đề xuất vay: {loan_requested:,.0f} VNĐ
- Mục đích vay: {loan_purpose}

### TỔNG HỢP KẾT QUẢ TỪ CÁC PHÂN HỆ:
1. **Lịch sử CIC & CRM (Node 1):**
   - Tên công ty: {cic_data.get('company_name', 'N/A')}
   - Nhóm nợ hiện tại: {cic_data.get('debt_group', 'N/A')}
   - Điểm tín dụng CIC: {cic_data.get('credit_score', 0)}
   - Lịch sử nợ quá hạn (36M): {cic_data.get('overdue_36m_count', 0)} lần
   - Tổng dư nợ hiện tại: {cic_data.get('total_current_debt', 0.0):,.0f} VNĐ

2. **Chỉ số Tài chính - Python Engine (Node 2):**
   - Hệ số Nợ / VCSH (D/E): {financial_data.get('de_ratio', 0.0)} (Ngưỡng an toàn: <= {financial_data.get('de_benchmark', 2.5)})
   - Hệ số Khả năng Trả nợ (DSCR): {financial_data.get('dscr', 0.0)} (Ngưỡng an toàn: >= {financial_data.get('dscr_benchmark', 1.2)})
   - Cảnh báo tài chính: {financial_data.get('warning_notes', [])}

3. **Tuân thủ Pháp lý - RAG Engine (Node 3):**
   - Trạng thái tuân thủ: {'HỢP LỆ' if legal_data.get('is_compliant') else 'VI PHẠM QUY ĐỊNH'}
   - Chi tiết vi phạm: {legal_data.get('violations', [])}
   - Cảnh báo rủi ro pháp lý: {legal_data.get('warnings', [])}

### QUY TẮC PHÁN QUYẾT TÍN DỤNG:
- **TỪ CHỐI CẤP TÍN DỤNG:** Nếu vi phạm điều cấm pháp lý (Node 3) HOẶC Nhóm nợ CIC >= Nhóm 3 HOẶC D/E quá cao (> 4.0).
- **CẦN BỔ SUNG HỒ SƠ:** Nếu rơi vào Nhóm nợ 2 HOẶC chỉ số DSCR yếu (< 1.2) HOẶC có Cảnh báo pháp lý cần làm rõ.
- **ĐỒNG Ý CẤP TÍN DỤNG:** Nếu tuân thủ pháp lý, Nhóm nợ 1, D/E và DSCR đều nằm trong ngưỡng an toàn.

Hãy tổng hợp và tạo Tờ trình Thẩm định Tín dụng bằng định dạng Markdown đầy đủ các mục:
I. Báo cáo Tóm tắt & Đề xuất Hạn mức
II. Đánh giá Khả năng Trả nợ & Chỉ số Tài chính
III. Đánh giá Tín nhiệm CIC & Tuân thủ Pháp lý
IV. Kết luận & Điều kiện Cấp tín dụng bổ sung.
"""

    # 4. Thực thi LLM
    assessment_result: UnderwritingAssessmentSchema = await structured_llm.ainvoke(system_prompt)

    # 5. Soạn Message kết quả hiển thị cho UI
    status_msg = (
        f"📝 **[Underwriting Specialist Node]:** Đã hoàn tất lập Tờ trình Thẩm định Tín dụng!\n"
        f"- **Quyết định đề xuất:** `{assessment_result.decision.value}`\n"
        f"- **Hạn mức phê duyệt:** `{assessment_result.recommended_credit_limit:,.0f} VNĐ`\n"
        f"- **Mức độ Rủi ro:** `{assessment_result.risk_level}`\n"
    )
    completed = state.get("completed_steps", []) + ["node_underwriting_specialist"]
    return {
        "assessment_result": assessment_result.model_dump(),
        "completed_steps": completed,
        "messages": [AIMessage(content=status_msg)]
    }
