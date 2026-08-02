from typing import Dict, Any
from langchain_core.messages import AIMessage
from src.schemas.underwriting_state import UnderwritingState
from src.schemas.financial_schema import FinancialAnalysisSchema


async def financial_calculator_node(state: UnderwritingState) -> Dict[str, Any]:
    """
    Node 2: Động cơ Python tính toán chính xác 100% các hệ số đòn bẩy & khả năng trả nợ.
    """
    cic_status = state.get("cic_status", {})

    # Bốc số liệu tài chính thô từ State (do Node 1 cung cấp từ CSV)
    total_liabilities = float(cic_status.get("total_liabilities", 0.0))
    owner_equity = float(cic_status.get("owner_equity", 1.0))
    ebitda = float(cic_status.get("ebitda", 0.0))
    annual_debt_service = float(cic_status.get("annual_debt_service", 1.0))

    # Tránh lỗi ZeroDivisionError
    if owner_equity <= 0:
        owner_equity = 1.0
    if annual_debt_service <= 0:
        annual_debt_service = 1.0

    # 1. TÍNH TOÁN CÁC HỆ SỐ TÀI CHÍNH (Python Execution)
    de_ratio = round(total_liabilities / owner_equity, 2)
    dscr = round(ebitda / annual_debt_service, 2)

    # Benchmarks quy định của Ngân hàng
    DE_BENCHMARK = 2.5   # Hệ số Nợ/VCSH tối đa cho phép
    DSCR_BENCHMARK = 1.2  # Hệ số Trả nợ tối thiểu cho phép

    # 2. ĐÁNH GIÁ VỚI QUY CHUẨN AN TOÀN
    is_de_safe = de_ratio <= DE_BENCHMARK
    is_dscr_safe = dscr >= DSCR_BENCHMARK
    is_healthy = is_de_safe and is_dscr_safe

    warnings = []
    if not is_de_safe:
        warnings.append(
            f"⚠️ CẢNH BÁO ĐÒN BẨY: Hệ số Nợ/VCSH (D/E = {de_ratio}) vượt ngưỡng an toàn (<= {DE_BENCHMARK}). Doanh nghiệp dùng đòn bẩy quá cao!"
        )
    if not is_dscr_safe:
        warnings.append(
            f"⚠️ CẢNH BÁO TRẢ NỢ: Hệ số Khả năng Trả nợ (DSCR = {dscr}) dưới ngưỡng an toàn (>= {DSCR_BENCHMARK}). Dòng tiền yếu!"
        )

    financial_result = FinancialAnalysisSchema(
        de_ratio=de_ratio,
        dscr=dscr,
        de_benchmark=DE_BENCHMARK,
        dscr_benchmark=DSCR_BENCHMARK,
        is_de_safe=is_de_safe,
        is_dscr_safe=is_dscr_safe,
        is_financial_healthy=is_healthy,
        warning_notes=warnings
    )

    # 3. TẠO MESSAGE HIỂN THỊ DẠNG MARKDOWN CHO UI
    status_msg = (
        f"📊 **[Financial Calculator Node]:** Đã phân tích xong BCTC.\n"
        f"- **Hệ số Nợ / VCSH (D/E):** `{de_ratio}` (Chuẩn: <= {DE_BENCHMARK}) ──► {'✅ An toàn' if is_de_safe else '❌ Rủi ro cao'}\n"
        f"- **Hệ số Trả nợ (DSCR):** `{dscr}` (Chuẩn: >= {DSCR_BENCHMARK}) ──► {'✅ Đạt' if is_dscr_safe else '❌ Yếu'}\n"
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
