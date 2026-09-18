from typing import Dict, Any
from langchain_core.messages import AIMessage
from src.schemas.underwriting_state import UnderwritingState
from src.schemas.financial_schema import FinancialAnalysisSchema


async def financial_calculator_node(state: UnderwritingState) -> Dict[str, Any]:
    """
    Node 2: Động cơ Python tính toán chính xác 100% các hệ số đòn bẩy & khả năng trả nợ.
    """
    cic_status = state.get("cic_status", {})
    loan_requested = float(state.get("loan_amount_requested", 0.0))

    # Bốc số liệu tài chính thô từ State (do Node 1 cung cấp từ CSV)
    total_liabilities = float(cic_status.get("total_liabilities", 0.0))
    owner_equity = float(cic_status.get("owner_equity", 1.0))
    ebitda = float(cic_status.get("ebitda", 0.0))
    annual_debt_service = float(cic_status.get("annual_debt_service", 1.0))

    safe_equity = owner_equity if owner_equity > 0 else 1.0
    safe_debt_service = annual_debt_service if annual_debt_service > 0 else 1.0

    # 1. TÍNH TOÁN CÁC HỆ SỐ TÀI CHÍNH (Python Execution)
    de_ratio = round(total_liabilities / safe_equity, 2)
    pro_forma_de = round((total_liabilities + loan_requested) / safe_equity, 2)
    max_safe_limit = max(0.0, round(2.5 * safe_equity - total_liabilities, -6))
    dscr = round(ebitda / safe_debt_service, 2)

    # Benchmarks quy định của Ngân hàng
    DE_BENCHMARK = 2.5   # Hệ số Nợ/VCSH tối đa cho phép
    DSCR_BENCHMARK = 1.2  # Hệ số Trả nợ tối thiểu cho phép

    # 2. ĐÁNH GIÁ VỚI QUY CHUẨN AN TOÀN
    is_de_safe = de_ratio <= DE_BENCHMARK
    is_dscr_safe = dscr >= DSCR_BENCHMARK
    is_healthy = is_de_safe and is_dscr_safe and (pro_forma_de <= DE_BENCHMARK)

    warnings = []
    if de_ratio > DE_BENCHMARK:
        warnings.append(
            f"⚠️ CẢNH BÁO ĐÒN BẨY HIỆN TẠI: Hệ số Nợ/VCSH (D/E = {de_ratio}) vượt ngưỡng an toàn (<= {DE_BENCHMARK}). Doanh nghiệp dùng đòn bẩy quá cao!"
        )
    if pro_forma_de > 4.0:
        warnings.append(
            f"🚨 CẢNH BÁO NGUY HIỂM: Khoản vay mới đẩy D/E dự phóng lên {pro_forma_de} (> 4.0). Vốn CSH không đủ năng lực gánh nợ!"
        )
    elif pro_forma_de > DE_BENCHMARK:
        warnings.append(
            f"⚠️ CẢNH BÁO ĐÒN BẨY SAU VAY: Khoản vay mới đẩy D/E dự phóng lên {pro_forma_de} (> {DE_BENCHMARK}). Khuyến nghị hạn mức an toàn: {max_safe_limit:,.0f} VNĐ."
        )

    if not is_dscr_safe:
        warnings.append(
            f"⚠️ CẢNH BÁO TRẢ NỢ: Hệ số Khả năng Trả nợ (DSCR = {dscr}) dưới ngưỡng an toàn (>= {DSCR_BENCHMARK}). Dòng tiền yếu!"
        )

    financial_result = FinancialAnalysisSchema(
        de_ratio=de_ratio,
        pro_forma_de=pro_forma_de,
        max_safe_limit=max_safe_limit,
        dscr=dscr,
        de_benchmark=DE_BENCHMARK,
        dscr_benchmark=DSCR_BENCHMARK,
        is_de_safe=is_de_safe,
        is_dscr_safe=is_dscr_safe,
        is_financial_healthy=is_healthy,
        warning_notes=warnings,
        equity=owner_equity,
        total_liabilities=total_liabilities,
        ebitda=ebitda,
        annual_debt_service=annual_debt_service,
    )

    # 3. TẠO MESSAGE HIỂN THỊ DẠNG MARKDOWN 
    status_msg = (
        f"📊 **[Financial Calculator Node]:** Đã phân tích xong BCTC.\n"
        f"- **Hệ số Nợ / VCSH (D/E):** `{de_ratio}` ➔ **D/E Sau vay:** `{pro_forma_de}` (Chuẩn: <= {DE_BENCHMARK})\n"
        f"- **Hệ số Trả nợ (DSCR):** `{dscr}` (Chuẩn: >= {DSCR_BENCHMARK}) ──► {'✅ Đạt' if is_dscr_safe else '❌ Yếu'}\n"
        f"- **Hạn mức an toàn tối đa (VCSH):** `{max_safe_limit:,.0f} VNĐ`\n"
        f"- **Sức khỏe Tài chính Chung:** {'🟢 LÀNH MẠNH' if is_healthy else '🔴 CÓ RỦI RO'}\n"
    )
    if warnings:
        status_msg += "\n" + "\n".join(warnings)
    completed = state.get("completed_steps", []) + ["node_financial_calc"]
    return {
        "financial_ratios": financial_result.model_dump(),
        "completed_steps": completed,
        "messages": [AIMessage(content=status_msg)]
    }
