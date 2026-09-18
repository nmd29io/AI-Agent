import os
from typing import Dict, Any
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.schemas.underwriting_state import UnderwritingState
from src.schemas.underwriting_schema import (
    UnderwritingAssessmentSchema,
    LLMAssessmentOutput,
    CreditDecisionEnum,
)
from src.services.credit_report_template import render_credit_appraisal_report, format_currency_vnd


def _rule_based_fallback_assessment(state: UnderwritingState) -> UnderwritingAssessmentSchema:
    """Động cơ phán quyết tín dụng theo luật định chuẩn nghiệp vụ ngân hàng (Fallback)."""
    tax_code = state.get("company_tax_code", "N/A")
    loan_requested = float(state.get("loan_amount_requested", 0.0))
    cic_data = state.get("cic_status", {})
    financial_data = state.get("financial_ratios", {})
    legal_data = state.get("legal_compliance", {})

    debt_group = str(cic_data.get("debt_group", ""))
    de_ratio = float(financial_data.get("de_ratio", 0.0))
    pro_forma_de = float(financial_data.get("pro_forma_de", de_ratio))
    dscr = float(financial_data.get("dscr", 0.0))
    max_safe_limit = float(financial_data.get("max_safe_limit", 0.0))
    equity = float(cic_data.get("owner_equity", 1.0))
    is_legal_compliant = legal_data.get("is_compliant", True)

    is_bad_cic = any(x in debt_group for x in ["Nhóm 3", "Nhóm 4", "Nhóm 5"])
    is_warning_cic = "Nhóm 2" in debt_group

    strengths = []
    risks = []
    conditions_prec = [
        "Cung cấp đầy đủ hồ sơ pháp lý, đăng ký kinh doanh và điều lệ doanh nghiệp cập nhật hợp lệ.",
        "Cung cấp Hợp đồng kinh tế đầu vào/đầu ra, hóa đơn GTGT hợp lệ chứng minh phương án sử dụng vốn đúng mục đích.",
        "Ký kết Hợp đồng tín dụng, Hợp đồng thế chấp và hoàn tất thủ tục công chứng, đăng ký biện pháp bảo đảm (nếu có yêu cầu TSĐB).",
        "Cam kết mở tài khoản thanh toán và chuyển tối thiểu 80% doanh thu bán hàng về tài khoản tại ngân hàng."
    ]
    post_monitoring = [
        "Thực hiện kiểm tra mục đích sử dụng vốn vay trong vòng 30 ngày kể từ ngày giải ngân từng khế ước nhận nợ.",
        "Định kỳ hàng quý rà soát Báo cáo tài chính, tờ khai thuế GTGT và sao kê tài khoản doanh thu của khách hàng.",
        "Giám sát chặt chẽ trạng thái tín dụng CIC tại các TCTD khác để cảnh báo sớm nếu phát sinh nợ quá hạn.",
        "Duy trì tỷ lệ an toàn tài chính: Đảm bảo hệ số D/E không vượt quá 2.5 và DSCR không thấp hơn 1.2 trong suốt thời hạn vay."
    ]

    # 1. BẮT BUỘC TỪ CHỐI
    if not is_legal_compliant or de_ratio > 4.0 or pro_forma_de > 4.0 or dscr < 1.0 or is_bad_cic:
        decision = CreditDecisionEnum.REJECT
        limit = 0.0
        risk_level = "Rất cao"
        reasons = []
        if not is_legal_compliant:
            reasons.append("Mục đích vay vốn vi phạm quy định pháp lý cấm cho vay theo Thông tư 39/2016/TT-NHNN")
            risks.append("Vi phạm quy định pháp lý bắt buộc của Ngân hàng Nhà nước.")
        if is_bad_cic:
            reasons.append(f"Lịch sử tín dụng CIC xấu ({debt_group})")
            risks.append(f"CIC thuộc nhóm nợ xấu ({debt_group}), điểm tín dụng rất thấp.")
        if de_ratio > 4.0:
            reasons.append(f"Đòn bẩy tài chính hiện tại quá cao (D/E = {de_ratio:.2f} > 4.0)")
            risks.append(f"Hệ số đòn bẩy tài chính Nợ/VCSH hiện tại (D/E = {de_ratio:.2f}) vượt xa mức an toàn.")
        if pro_forma_de > 4.0 and de_ratio <= 4.0:
            reasons.append(
                f"Khoản vay đề nghị ({format_currency_vnd(loan_requested)}) vượt quá xa năng lực vốn CSH ({format_currency_vnd(equity)}), đẩy D/E sau vay lên {pro_forma_de:.2f} (> 4.0)"
            )
            risks.append(f"Đòn bẩy dự phóng sau giải ngân (Pro-forma D/E = {pro_forma_de:.2f}) vượt trần từ chối 4.0.")
        if dscr < 1.0:
            reasons.append(f"Khả năng trả nợ yếu (DSCR = {dscr:.2f} < 1.0)")
            risks.append(f"Khả năng trả nợ không bảo đảm (DSCR = {dscr:.2f} < 1.0), thâm hụt dòng tiền thanh toán nợ.")
        summary = "Từ chối cấp tín dụng do: " + "; ".join(reasons) + "."

    # 2. CẦN BỔ SUNG HỒ SƠ / TÀI SẢN ĐẢM BẢO
    elif is_warning_cic or de_ratio > 2.5 or pro_forma_de > 2.5 or dscr < 1.2 or legal_data.get("has_warnings"):
        decision = CreditDecisionEnum.MORE_INFO
        limit = min(loan_requested, max_safe_limit if max_safe_limit > 0 else round(loan_requested * 0.7, -6))
        risk_level = "Trung bình"
        reasons = []
        if is_warning_cic:
            reasons.append(f"CIC thuộc {debt_group}")
            risks.append(f"Khách hàng thuộc {debt_group}, có lịch sử nợ quá hạn cần theo dõi.")
        if de_ratio > 2.5:
            reasons.append(f"Hệ số D/E hiện tại = {de_ratio:.2f} > 2.5")
            risks.append(f"Đòn bẩy tài chính hiện tại cao (D/E = {de_ratio:.2f} > 2.5).")
        if pro_forma_de > 2.5 and de_ratio <= 2.5:
            reasons.append(f"Khoản vay đẩy D/E sau vay lên {pro_forma_de:.2f} > 2.5")
            risks.append(f"Quy mô khoản vay đẩy đòn bẩy sau vay lên {pro_forma_de:.2f} vượt trần an toàn 2.5.")
        if dscr < 1.2:
            reasons.append(f"Hệ số DSCR = {dscr:.2f} < 1.2")
            risks.append(f"Hệ số DSCR = {dscr:.2f} dưới mức an toàn 1.2, cần giám sát dòng tiền chặt chẽ.")
        summary = f"Cần bổ sung tài sản đảm bảo thanh khoản cao hoặc giảm quy mô vay: {'; '.join(reasons)}. Khuyến nghị hạn mức an toàn: {format_currency_vnd(limit)}."
        strengths.append("Doanh nghiệp có năng lực hoạt động và phương án kinh doanh cụ thể.")
        conditions_prec.append(f"Bổ sung tài sản đảm bảo bằng Bất động sản/Tiền gửi có giá trị tối thiểu bằng 120% hạn mức cấp tín dụng ({format_currency_vnd(limit)}).")

    # 3. ĐỒNG Ý CẤP TÍN DỤNG
    else:
        decision = CreditDecisionEnum.APPROVE
        limit = min(loan_requested, max_safe_limit if max_safe_limit > 0 else loan_requested)
        risk_level = "Thấp"
        summary = "Hồ sơ đáp ứng đầy đủ tiêu chuẩn tín dụng, an toàn tài chính, đòn bẩy sau giải ngân nằm trong trần an toàn và quy mô khoản vay hoàn toàn phù hợp với năng lực vốn chủ sở hữu."
        strengths.append("Mục đích vay vốn hợp pháp, tuân thủ Thông tư 39/2016/TT-NHNN.")
        strengths.append(f"Lịch sử tín dụng CIC tốt ({debt_group}), không có nợ quá hạn.")
        strengths.append(f"Cấu trúc tài chính lành mạnh: D/E hiện tại = {de_ratio:.2f} <= 2.5; D/E sau vay = {pro_forma_de:.2f} <= 2.5.")
        strengths.append(f"Khả năng trả nợ tốt: DSCR = {dscr:.2f} >= 1.2.")
        risks.append("Kiểm soát chặt chẽ dòng tiền doanh thu bán hàng về tài khoản tại ngân hàng.")

    report_md = render_credit_appraisal_report(
        state=state,
        decision=decision.value,
        recommended_credit_limit=limit,
        risk_level=risk_level,
        summary_notes=summary,
        key_strengths=strengths,
        key_risks=risks,
        conditions_precedent=conditions_prec,
        post_disbursement_monitoring=post_monitoring,
    )

    return UnderwritingAssessmentSchema(
        decision=decision,
        recommended_credit_limit=limit,
        risk_level=risk_level,
        summary_notes=summary,
        key_strengths=strengths,
        key_risks=risks,
        conditions_precedent=conditions_prec,
        post_disbursement_monitoring=post_monitoring,
        submission_report_markdown=report_md,
        markdown_report=report_md,
    )


async def underwriting_specialist_node(state: UnderwritingState) -> Dict[str, Any]:
    """
    Node 4: AI Underwriting Specialist - Phân tích dữ liệu đa phân hệ và sinh Tờ trình Thẩm định Tín dụng chuẩn nghiệp vụ.
    """
    tax_code = state.get("company_tax_code", "N/A")
    comp_name = state.get("company_name", "Doanh nghiệp")
    loan_requested = float(state.get("loan_amount_requested", 0.0))
    loan_purpose = state.get("loan_purpose", "N/A")

    cic_data = state.get("cic_status", {})
    financial_data = state.get("financial_ratios", {})
    legal_data = state.get("legal_compliance", {})

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if api_key:
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=api_key,
                temperature=0.2,
                request_timeout=25,
            )
            structured_llm = llm.with_structured_output(LLMAssessmentOutput)

            system_prompt = f"""
Bạn là Chuyên viên Thẩm định Tín dụng Doanh nghiệp Cấp cao tại Ngân hàng.
Nhiệm vụ của bạn là phân tích toàn bộ dữ liệu hồ sơ và đưa ra phán quyết, đánh giá rủi ro, điểm mạnh, điều kiện cấp tín dụng:

### THÔNG TIN YÊU CẦU KHOẢN VAY:
- Doanh nghiệp: {comp_name} (MST: {tax_code})
- Số tiền đề xuất vay: {loan_requested:,.0f} VNĐ
- Mục đích vay: {loan_purpose}

### TỔNG HỢP KẾT QUẢ TỪ CÁC PHÂN HỆ:
1. **Lịch sử CIC & CRM (Node 1):**
   - Tên công ty: {cic_data.get('company_name', comp_name)}
   - Nhóm nợ hiện tại: {cic_data.get('debt_group', 'N/A')}
   - Điểm tín dụng CIC: {cic_data.get('credit_score', 0)}
   - Lịch sử nợ quá hạn (36M): {cic_data.get('overdue_36m_count', 0)} lần
   - Tổng dư nợ hiện tại: {float(cic_data.get('total_current_debt', 0.0)):,.0f} VNĐ

2. **Chỉ số Tài chính - Python Engine (Node 2):**
   - Vốn CSH: {float(financial_data.get('equity', cic_data.get('owner_equity', 0.0))):,.0f} VNĐ | EBITDA: {float(financial_data.get('ebitda', cic_data.get('ebitda', 0.0))):,.0f} VNĐ
   - Hệ số D/E hiện tại: {financial_data.get('de_ratio', 0.0)} (Ngưỡng an toàn: <= 2.5)
   - Hệ số D/E dự phóng sau giải ngân (Pro-forma D/E): {financial_data.get('pro_forma_de', 0.0)} (Trần an toàn <= 2.5, Bắt buộc TỪ CHỐI nếu > 4.0)
   - Hệ số Khả năng Trả nợ (DSCR): {financial_data.get('dscr', 0.0)} (Ngưỡng an toàn: >= 1.2)
   - Hạn mức vay an toàn tối đa theo VCSH: {float(financial_data.get('max_safe_limit', 0.0)):,.0f} VNĐ
   - Cảnh báo tài chính: {financial_data.get('warning_notes', [])}

3. **Tuân thủ Pháp lý - RAG Engine (Node 3):**
   - Trạng thái tuân thủ: {'HỢP LỆ' if legal_data.get('is_compliant') else 'VI PHẠM QUY ĐỊNH'}
   - Chi tiết vi phạm: {legal_data.get('violations', [])}
   - Cảnh báo rủi ro pháp lý: {legal_data.get('warnings', [])}

### QUY TẮC PHÁN QUYẾT BẮT BUỘC:
- **TỪ CHỐI CẤP TÍN DỤNG:** Nếu vi phạm điều cấm pháp lý (Thông tư 39) HOẶC Nhóm nợ CIC >= Nhóm 3 HOẶC Pro-forma D/E > 4.0 HOẶC DSCR < 1.0. Hạn mức = 0.
- **CẦN BỔ SUNG HỒ SƠ:** Nếu rơi vào Nhóm nợ 2 HOẶC Pro-forma D/E nằm trong khoảng 2.5 - 4.0 HOẶC DSCR 1.0 - 1.2. Hạn mức đề xuất <= hạn mức an toàn ({float(financial_data.get('max_safe_limit', 0.0)):,.0f} VNĐ).
- **ĐỒNG Ý CẤP TÍN DỤNG:** Nếu tuân thủ pháp lý, Nhóm nợ 1, D/E sau vay <= 2.5 và DSCR >= 1.2.

Hãy đánh giá cẩn trọng và trích xuất:
- decision: APPROVE / REJECT / MORE_INFO
- recommended_credit_limit: số tiền đề xuất tối đa (float)
- risk_level: Thấp / Trung bình / Cao / Rất cao
- summary_notes: tóm tắt lý do cốt lõi
- key_strengths: danh sách các điểm mạnh
- key_risks: danh sách các rủi ro chính
- conditions_precedent: điều kiện tiên quyết trước giải ngân
- post_disbursement_monitoring: điều kiện quản lý sau giải ngân
"""
            llm_out: LLMAssessmentOutput = await structured_llm.ainvoke(system_prompt)

            # Tạo Tờ trình Thẩm định chuẩn nghiệp vụ ngân hàng 7 phần đầy đủ bảng biểu
            report_md = render_credit_appraisal_report(
                state=state,
                decision=llm_out.decision.value,
                recommended_credit_limit=llm_out.recommended_credit_limit,
                risk_level=llm_out.risk_level,
                summary_notes=llm_out.summary_notes,
                key_strengths=llm_out.key_strengths,
                key_risks=llm_out.key_risks,
                conditions_precedent=llm_out.conditions_precedent,
                post_disbursement_monitoring=llm_out.post_disbursement_monitoring,
            )
            assessment_result = UnderwritingAssessmentSchema(
                **llm_out.model_dump(),
                submission_report_markdown=report_md,
                markdown_report=report_md,
            )
        except Exception:
            assessment_result = _rule_based_fallback_assessment(state)
    else:
        assessment_result = _rule_based_fallback_assessment(state)

    status_msg = (
        f"📝 **[Underwriting Specialist Node]:** Đã hoàn tất lập Tờ trình Thẩm định Tín dụng cho {comp_name}!\n"
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
