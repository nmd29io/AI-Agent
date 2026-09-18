from datetime import datetime
from typing import Any, Dict, List, Optional


def format_currency_vnd(amount: float) -> str:
    """Định dạng số tiền sang định dạng tiền tệ VNĐ (ví dụ: 8.000.000.000 VNĐ)."""
    try:
        val = float(amount)
        return f"{val:,.0f}".replace(",", ".") + " VNĐ"
    except (ValueError, TypeError):
        return "0 VNĐ"


def render_credit_appraisal_report(
    state: Dict[str, Any],
    decision: str,
    recommended_credit_limit: float,
    risk_level: str,
    summary_notes: str,
    key_strengths: Optional[List[str]] = None,
    key_risks: Optional[List[str]] = None,
    conditions_precedent: Optional[List[str]] = None,
    post_disbursement_monitoring: Optional[List[str]] = None,
) -> str:
    """
    Tạo Tờ trình Thẩm định Tín dụng Doanh nghiệp chuẩn nghiệp vụ ngân hàng
    với đầy đủ cấu trúc 7 phần chuyên nghiệp và bảng biểu Markdown chi tiết.
    """
    now = datetime.now()
    report_date = now.strftime("%d/%m/%Y")
    report_time = now.strftime("%H:%M:%S")

    # Dữ liệu khách hàng và khoản vay
    tax_code = str(state.get("company_tax_code", "N/A")).strip()
    company_name = state.get("company_name", "Doanh nghiệp").strip()
    loan_requested = float(state.get("loan_amount_requested", 0.0))
    loan_purpose = state.get("loan_purpose", "Bổ sung vốn kinh doanh").strip()

    # Dữ liệu CIC
    cic = state.get("cic_status", {})
    est_year = cic.get("establishment_year", "N/A")
    debt_group = cic.get("debt_group", "Nhóm 1 - Nợ chuẩn")
    credit_score = cic.get("credit_score", 0)
    overdue_36m = cic.get("overdue_36m_count", 0)
    total_current_debt = float(cic.get("total_current_debt", 0.0))
    internal_rating = cic.get("internal_rating", "BBB")

    # Dữ liệu Tài chính
    fin = state.get("financial_ratios", {})
    equity = float(fin.get("equity", cic.get("owner_equity", 0.0)))
    total_liabilities = float(fin.get("total_liabilities", cic.get("total_liabilities", 0.0)))
    ebitda = float(fin.get("ebitda", cic.get("ebitda", 0.0)))
    debt_service = float(fin.get("annual_debt_service", cic.get("annual_debt_service", 0.0)))

    de_ratio = fin.get("de_ratio", round(total_liabilities / (equity if equity > 0 else 1.0), 2))
    pro_forma_de = fin.get(
        "pro_forma_de",
        round((total_liabilities + loan_requested) / (equity if equity > 0 else 1.0), 2),
    )
    dscr = fin.get("dscr", round(ebitda / (debt_service if debt_service > 0 else 1.0), 2))
    max_safe_limit = float(fin.get("max_safe_limit", 0.0))

    # Dữ liệu Pháp lý
    legal = state.get("legal_compliance", {})
    is_legal_compliant = legal.get("is_compliant", True)
    legal_violations = legal.get("violations", [])
    legal_warnings = legal.get("warnings", [])
    cited_articles = legal.get("cited_articles", [])

    # Chuẩn hóa phán quyết
    decision_str = str(decision.value if hasattr(decision, "value") else decision).upper()
    if "ĐỒNG Ý" in decision_str or "APPROVE" in decision_str:
        status_badge = "🟢 ĐỒNG Ý CẤP TÍN DỤNG"
    elif "BỔ SUNG" in decision_str or "MORE_INFO" in decision_str or "REQUIRE" in decision_str:
        status_badge = "🟡 CẦN BỔ SUNG HỒ SƠ & TÀI SẢN ĐẢM BẢO"
    else:
        status_badge = "🔴 TỪ CHỐI CẤP TÍN DỤNG"

    # Mặc định danh sách điểm mạnh nếu chưa có
    if not key_strengths:
        key_strengths = []
        if is_legal_compliant:
            key_strengths.append("Mục đích vay vốn hợp pháp, không thuộc các hành vi bị cấm theo Thông tư 39/2016/TT-NHNN.")
        if "Nhóm 1" in str(debt_group) and overdue_36m == 0:
            key_strengths.append(f"Lịch sử tín dụng CIC tốt ({debt_group}), không phát sinh nợ quá hạn trong 36 tháng.")
        if de_ratio <= 2.5:
            key_strengths.append(f"Cơ cấu đòn bẩy tài chính hiện tại an toàn (D/E = {de_ratio:.2f} <= 2.5).")
        if dscr >= 1.2:
            key_strengths.append(f"Dòng tiền trả nợ dồi dào, khả năng hấp thụ nợ tốt (DSCR = {dscr:.2f} >= 1.2).")
        if not key_strengths:
            key_strengths.append("Doanh nghiệp có cơ sở hoạt động thực tế và nhu cầu vốn rõ ràng.")

    # Mặc định danh sách rủi ro nếu chưa có
    if not key_risks:
        key_risks = []
        if not is_legal_compliant:
            key_risks.append(f"Rủi ro pháp lý nghiêm trọng: {', '.join(legal_violations) if legal_violations else 'Vi phạm quy định TT 39/2016/TT-NHNN'}.")
        if pro_forma_de > 4.0:
            key_risks.append(f"Đòn bẩy sau giải ngân quá mức cho phép: D/E dự phóng = {pro_forma_de:.2f} (> 4.0). Vốn CSH không đủ năng lực gánh nợ.")
        elif pro_forma_de > 2.5:
            key_risks.append(f"Khoản vay mới làm gia tăng đòn bẩy tài chính: D/E dự phóng = {pro_forma_de:.2f} (> ngưỡng chuẩn 2.5).")
        if dscr < 1.0:
            key_risks.append(f"Áp lực trả nợ lớn: DSCR = {dscr:.2f} (< 1.0) không đủ nguồn thu EBITDA trang trải nợ vay.")
        elif dscr < 1.2:
            key_risks.append(f"Biên độ an toàn dòng tiền thấp: DSCR = {dscr:.2f} (< chuẩn an toàn 1.2).")
        if any(x in str(debt_group) for x in ["Nhóm 2", "Nhóm 3", "Nhóm 4", "Nhóm 5"]) or overdue_36m > 0:
            key_risks.append(f"Lịch sử tín dụng có tì vết: {debt_group}, ghi nhận {overdue_36m} lần quá hạn 36 tháng.")
        if not key_risks:
            key_risks.append(f"Kiểm soát dòng tiền doanh thu để đảm bảo không bị thất thoát sang các nghĩa vụ khác (Tổng dư nợ hiện hữu {format_currency_vnd(total_current_debt)}).")

    # Mặc định điều kiện tiên quyết trước giải ngân
    if not conditions_precedent:
        conditions_precedent = [
            "Cung cấp đầy đủ hồ sơ pháp lý, đăng ký kinh doanh và điều lệ doanh nghiệp cập nhật hợp lệ.",
            "Cung cấp Hợp đồng kinh tế đầu vào/đầu ra, hóa đơn GTGT hợp lệ chứng minh phương án sử dụng vốn đúng mục đích.",
            "Ký kết Hợp đồng tín dụng, Hợp đồng thế chấp và hoàn tất thủ tục công chứng, đăng ký biện pháp bảo đảm (nếu có yêu cầu TSĐB).",
            "Cam kết mở tài khoản thanh toán và chuyển tối thiểu 80% doanh thu bán hàng về tài khoản tại ngân hàng."
        ]

    # Mặc định điều kiện quản lý sau giải ngân
    if not post_disbursement_monitoring:
        post_disbursement_monitoring = [
            "Thực hiện kiểm tra mục đích sử dụng vốn vay trong vòng 30 ngày kể từ ngày giải ngân từng khế ước nhận nợ.",
            "Định kỳ hàng quý rà soát Báo cáo tài chính, tờ khai thuế GTGT và sao kê tài khoản doanh thu của khách hàng.",
            "Giám sát chặt chẽ trạng thái tín dụng CIC tại các TCTD khác để cảnh báo sớm nếu phát sinh nợ quá hạn.",
            "Duy trì tỷ lệ an toàn tài chính: Đảm bảo hệ số D/E không vượt quá 2.5 và DSCR không thấp hơn 1.2 trong suốt thời hạn vay."
        ]

    # Định dạng Markdown Bảng biểu Tờ trình Thẩm định hoàn chỉnh
    report_md = f"""# 🏦 TỜ TRÌNH THẨM ĐỊNH TÍN DỤNG DOANH NGHIỆP
**NGÂN HÀNG THƯƠNG MẠI CỔ PHẦN - KHỐI KHÁCH HÀNG DOANH NGHIỆP**  
*Mã số Tờ trình: `TTTD-{tax_code}-{now.strftime('%Y%m%d')}` | Ngày lập: `{report_date}` ({report_time})*  
*Kính gửi:* **HỘI ĐỒNG TÍN DỤNG / CẤP PHÊ DUYỆT CÓ THẨM QUYỀN**

---

### 📌 KẾT QUẢ PHÁN QUYẾT TỔNG THỂ
| Chỉ tiêu | Kết quả thẩm định | Ghi chú & Đánh giá |
| :--- | :--- | :--- |
| **Quyết định thẩm định** | **{status_badge}** | Căn cứ thẩm định toàn diện 4 trụ cột |
| **Hạn mức đề xuất phê duyệt** | **`{format_currency_vnd(recommended_credit_limit)}`** | *(Nhu cầu xin vay: {format_currency_vnd(loan_requested)})* |
| **Mức độ Rủi ro Tổng thể** | **`{risk_level}`** | Theo khẩu vị rủi ro tín dụng doanh nghiệp |
| **Trần an toàn tối đa theo VCSH** | **`{format_currency_vnd(max_safe_limit)}`** | Giữ trần đòn bẩy D/E sau vay ≤ 2.5 |

---

### PHẦN I: THÔNG TIN CHUNG VỀ KHÁCH HÀNG & NHU CẦU CẤP TÍN DỤNG

#### 1.1. Thông tin Định danh & Pháp lý Doanh nghiệp
| Thông tin | Chi tiết hồ sơ |
| :--- | :--- |
| **Tên Doanh nghiệp** | **{company_name}** |
| **Mã số thuế (MST)** | `{tax_code}` |
| **Năm thành lập / Thâm niên** | {est_year} *(Hoạt động {max(1, now.year - int(est_year)) if str(est_year).isdigit() else 'N/A'} năm)* |
| **Xếp hạng tín dụng nội bộ** | Hạng `{internal_rating}` |
| **Tình trạng quan hệ tín dụng** | Đang có quan hệ tín dụng trong hệ thống CSDL Ngân hàng |

#### 1.2. Đề xuất Nhu cầu Vốn Vay từ Khách hàng
| Nội dung đề xuất | Chi tiết yêu cầu |
| :--- | :--- |
| **Số tiền đề nghị cấp tín dụng** | **`{format_currency_vnd(loan_requested)}`** |
| **Mục đích vay vốn cụ thể** | {loan_purpose} |
| **Hình thức cấp tín dụng** | Cho vay theo món / Hạn mức tín dụng tuần hoàn |
| **Thời hạn vay dự kiến** | 12 tháng (Bổ sung vốn lưu động) / Theo chu kỳ SXKD |
| **Nguồn trả nợ dự kiến** | Dòng tiền thu từ hoạt động sản xuất kinh doanh & doanh thu bán hàng |

---

### PHẦN II: THẨM ĐỊNH TƯ CÁCH PHÁP LÝ & QUY ĐỊNH NHNN (THÔNG TƯ 39/2016/TT-NHNN)

#### 2.1. Rà soát Điều kiện Cho vay & Điều cấm (Điều 8 TT 39/2016/TT-NHNN sửa đổi bởi TT 06/2023)
| Nội dung kiểm tra pháp lý | Trạng thái | Căn cứ & Đánh giá chi tiết |
| :--- | :---: | :--- |
| **Tư cách chủ thể & Năng lực pháp luật** | {'✅ ĐẠT' if is_legal_compliant else '❌ KHÔNG ĐẠT'} | Doanh nghiệp thành lập hợp pháp, người đại diện có đầy đủ thẩm quyền. |
| **Mục đích sử dụng vốn hợp pháp** | {'✅ HỢP LỆ' if is_legal_compliant else '❌ VI PHẠM'} | Rà soát mục đích vay: "{loan_purpose}". |
| **Rà soát danh mục cấm cho vay (Điều 8)** | {'✅ KHÔNG VI PHẠM' if is_legal_compliant else '❌ PHÁT HIỆN VI PHẠM'} | Không thuộc đối tượng cấm cho vay (chứng khoán, đảo nợ trái phép, BĐS không đủ điều kiện). |

#### 2.2. Chi tiết Vi phạm & Cảnh báo Pháp lý
- **Trạng thái tuân thủ:** **{'🟢 HOÀN TOÀN TUÂN THỦ' if is_legal_compliant else '🔴 VI PHẠM ĐIỀU CẤM PHÁP LÝ'}**
- **Nội dung vi phạm:** {', '.join(legal_violations) if legal_violations else 'Không có vi phạm pháp lý phát hiện.'}
- **Cảnh báo rủi ro pháp lý:** {', '.join(legal_warnings) if legal_warnings else 'Không có cảnh báo đặc biệt.'}
- **Căn cứ điều khoản trích dẫn:** {', '.join(cited_articles) if cited_articles else 'Thông tư 39/2016/TT-NHNN của Thống đốc Ngân hàng Nhà nước Việt Nam.'}

---

### PHẦN III: THẨM ĐỊNH LỊCH SỬ TÍN DỤNG & QUAN HỆ CIC (TRUNG TÂM THÔNG TIN TÍN DỤNG)

#### 3.1. Dữ liệu Lịch sử Tín dụng CIC
| Chỉ tiêu tra cứu CIC | Kết quả tra cứu | Ngưỡng chuẩn / Đánh giá |
| :--- | :--- | :--- |
| **Phân loại nhóm nợ hiện tại** | **`{debt_group}`** | Yêu cầu chuẩn: Nhóm 1 (Nợ đủ tiêu chuẩn) |
| **Điểm tín dụng CIC Quốc gia** | **`{credit_score}` điểm** | Thang điểm 150 - 850 (≥ 650: Tốt; < 500: Kém) |
| **Số lần nợ quá hạn (36 tháng qua)** | **`{overdue_36m}` lần** | Chuẩn an toàn: 0 lần nợ quá hạn |
| **Tổng dư nợ hiện tại tại các TCTD** | **`{format_currency_vnd(total_current_debt)}`** | Dư nợ đang được ghi nhận trên toàn hệ thống TCTD |

#### 3.2. Đánh giá Uy tín Trả nợ Khách hàng
- **Uy tín lịch sử tín dụng:** {
    'Khách hàng có lịch sử tín dụng trong sạch, luôn thực hiện nghĩa vụ trả nợ đúng hạn tại các ngân hàng.' 
    if ('Nhóm 1' in str(debt_group) and overdue_36m == 0) 
    else f'Khách hàng có lịch sử nợ quá hạn ({overdue_36m} lần) hoặc phân loại nhóm nợ cần chú ý ({debt_group}). Cần đánh giá kỹ năng lực trả nợ.'
}

---

### PHẦN IV: THẨM ĐỊNH NĂNG LỰC TÀI CHÍNH & KHẢ NĂNG TRẢ NỢ

#### 4.1. Chỉ tiêu Tài chính Cơ bản (Trích xuất Báo cáo Tài chính)
| Chỉ tiêu BCTC | Giá trị ghi nhận | Ý nghĩa thẩm định |
| :--- | :--- | :--- |
| **Vốn chủ sở hữu (VCSH)** | **`{format_currency_vnd(equity)}`** | Nguồn vốn tự có tham gia bảo đảm khả năng tự chủ |
| **Tổng nợ phải trả hiện tại** | **`{format_currency_vnd(total_liabilities)}`** | Tổng nghĩa vụ tài chính với đối tác và ngân hàng |
| **Lợi nhuận trước thuế, lãi vay & KH (EBITDA)** | **`{format_currency_vnd(ebitda)}`** | Dòng tiền thuần tạo ra từ hoạt động kinh doanh lõi |
| **Nghĩa vụ nợ gốc & lãi phải trả hàng năm** | **`{format_currency_vnd(debt_service)}`** | Áp lực trả nợ cố định của doanh nghiệp mỗi năm |

#### 4.2. Phân tích Chỉ số Đòn bẩy Tài chính & Khả năng Trả nợ
| Chỉ số Tài chính | Giá trị tính toán | Chuẩn an toàn | Đánh giá & Rủi ro |
| :--- | :---: | :---: | :--- |
| **Hệ số Nợ / VCSH hiện tại (D/E)** | **`{de_ratio:.2f}`** | ≤ 2.50 | {'✅ An toàn' if de_ratio <= 2.5 else '⚠️ Đòn bẩy cao (> 2.5)'} |
| **Hệ số D/E Dự phóng sau khi vay (Pro-forma D/E)** | **`{pro_forma_de:.2f}`** | ≤ 2.50 | {
    '✅ An toàn, nằm trong hạn mức hấp thụ vốn' if pro_forma_de <= 2.5 
    else ('⚠️ Vượt trần khuyến nghị 2.5 (Cần bổ sung TSĐB)' if pro_forma_de <= 4.0 else '🚨 NGUY HIỂM: Vượt ngưỡng từ chối 4.0')
} |
| **Hệ số Khả năng Trả nợ (DSCR)** | **`{dscr:.2f}`** | ≥ 1.20 | {'✅ Đạt yêu cầu nguồn thu' if dscr >= 1.2 else ('⚠️ Yếu (1.0 - 1.2)' if dscr >= 1.0 else '🚨 Mất cân đối dòng tiền (< 1.0)')} |
| **Hạn mức vay an toàn tối đa theo VCSH** | **`{format_currency_vnd(max_safe_limit)}`** | Theo VCSH | Ngưỡng cấp tín dụng tối đa để giữ D/E sau vay ≤ 2.5 |

#### 4.3. Nhận xét Năng lực Tài chính
- **Khả năng hấp thụ nợ:** {
    f'Năng lực vốn chủ sở hữu ({format_currency_vnd(equity)}) đủ lớn để bảo đảm quy mô khoản vay.' 
    if pro_forma_de <= 2.5 
    else f'Quy mô khoản vay ({format_currency_vnd(loan_requested)}) làm gia tăng đòn bẩy D/E lên {pro_forma_de:.2f}, tiềm ẩn rủi ro nếu thị trường biến động.'
}
- **Nguồn tiền trả nợ:** {
    f'Dòng tiền EBITDA hàng năm đạt {format_currency_vnd(ebitda)} đảm bảo bao phủ {dscr:.2f} lần nghĩa vụ trả nợ ({format_currency_vnd(debt_service)}).' 
    if dscr >= 1.2 
    else f'Dòng tiền tạo ra ở mức vừa phải so với nghĩa vụ trả nợ hàng năm. Cần yêu cầu biện pháp kiểm soát nguồn thu chặt chẽ.'
}

---

### PHẦN V: NHẬN DIỆN RỦI RO CHÍNH & BIỆN PHÁP GIẢM THIỂU

#### 5.1. Các Điểm mạnh Chính của Hồ sơ (Strengths)
{chr(10).join(f"- ✅ **Điểm mạnh {i+1}:** {s}" for i, s in enumerate(key_strengths))}

#### 5.2. Các Rủi ro Nhận diện & Biện pháp Quản trị (Risks & Mitigations)
| TT | Yếu tố Rủi ro Phát hiện | Biện pháp Phòng ngừa & Giảm thiểu Rủi ro |
| :---: | :--- | :--- |
"""

    # Ghép bảng rủi ro
    for idx, r in enumerate(key_risks):
        mitigation = "Yêu cầu tài sản bảo đảm thanh khoản cao và giám sát doanh thu qua tài khoản ngân hàng."
        if "pháp lý" in r.lower():
            mitigation = "Từ chối cấp tín dụng theo quy định bắt buộc của NHNN."
        elif "đòn bẩy" in r.lower() or "d/e" in r.lower():
            mitigation = f"Khống chế trần hạn mức vay tối đa không vượt quá {format_currency_vnd(max_safe_limit)} và yêu cầu tăng vốn tự có."
        elif "dscr" in r.lower() or "dòng tiền" in r.lower():
            mitigation = "Kiểm soát toàn bộ dòng tiền thanh toán của các hợp đồng đầu ra về tài khoản mở tại ngân hàng."
        elif "cic" in r.lower() or "quá hạn" in r.lower():
            mitigation = "Yêu cầu báo cáo giải trình nguyên nhân quá hạn và bổ sung bảo lãnh thanh toán của cổ đông lớn."

        report_md += f"| {idx+1} | {r} | {mitigation} |\n"

    report_md += f"""
---

### PHẦN VI: KẾT LUẬN & ĐỀ XUẤT CỦA BỘ PHẬN THẨM ĐỊNH

#### 6.1. Đề xuất Phán quyết Tín dụng
- **Phán quyết cuối cùng:** **{status_badge}**
- **Hạn mức cấp tín dụng đề xuất:** **`{format_currency_vnd(recommended_credit_limit)}`**
- **Mức độ rủi ro:** **`{risk_level}`**
- **Tóm tắt căn cứ phê duyệt:** {summary_notes}

#### 6.2. Điều kiện Tiên quyết Trước khi Giải ngân (Conditions Precedent)
{chr(10).join(f"{i+1}. {c}" for i, c in enumerate(conditions_precedent))}

#### 6.3. Điều kiện Quản lý & Giám sát Sau Giải ngân (Post-disbursement Monitoring)
{chr(10).join(f"{i+1}. {c}" for i, c in enumerate(post_disbursement_monitoring))}

---

### PHẦN VII: TRÌNH DUYỆT & CHỮ KÝ CÁC CẤP PHÊ DUYỆT

| **CÁN BỘ QUẢN LÝ KHÁCH HÀNG (RM)** | **CHUYÊN VIÊN THẨM ĐỊNH TÍN DỤNG** | **CẤP PHÊ DUYỆT CÓ THẨM QUYỀN** |
| :---: | :---: | :---: |
| *(Ký và ghi rõ họ tên)* | *(Ký và ghi rõ họ tên)* | *(Phê duyệt / Không phê duyệt)* |
| <br><br><br> | <br><br><br> | <br><br><br> |
| **Bộ phận Quản lý Khách hàng** | **Phòng Thẩm định & Quản trị Rủi ro** | **Hội đồng Tín dụng / Ban Giám đốc** |
"""
    return report_md.strip()
