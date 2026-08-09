import os
from typing import Dict, Any
from langchain_core.messages import AIMessage
from src.schemas.underwriting_state import UnderwritingState
from src.services.csv_banking_service import CSVBankingService  # Service đọc CSV của bạn

# Khởi tạo service đọc dữ liệu
banking_service = CSVBankingService()

async def cic_csv_node(state: UnderwritingState) -> Dict[str, Any]:
    tax_code = state.get("company_tax_code", "")
    
    # 1. Gọi Service lấy dữ liệu và GÁN VÀO BIẾN `cic_data`
    report = await banking_service.fetch_credit_report(tax_code)
    
    # Nếu không tìm thấy, tạo dict mặc định để tránh crash
    cic_data = report.model_dump() if report else {
        # "company_name": "Không tìm thấy doanh nghiệp",
        # # "debt_group": "N/A",
        # # "credit_score": 0,
        # # "overdue_36m_count": 0,
        # # "total_current_debt": 0.0
    }
    # Tạo log thông báo hiển thị cho RM Dashboard
    status_msg = (
        f"✅ **[CIC & CRM CSV Service]:** Đã tra cứu dữ liệu MST {tax_code}.\n"
        f"- **Tên doanh nghiệp:** {report.company_name}\n"
        f"- **Xếp hạng nội bộ:** {report.internal_rating}\n"
        f"- **Phân loại CIC:** {report.debt_group} (Điểm CIC: {report.credit_score})\n"
        f"- **Số lần nợ quá hạn (36M):** {report.overdue_36m_count} lần\n"
        f"- **Tổng dư nợ hiện tại:** {report.total_current_debt:,.0f} VNĐ"
    )
    # 2. Cập nhật completed_steps cho Supervisor Graph
    completed = list(state.get("completed_steps") or [])
    if "node_cic_crm" not in completed:
        completed.append("node_cic_crm")

    # 3. Trả về State (đảm bảo biến cic_data đã được định nghĩa ở trên)
    return {
        "cic_status": cic_data,
        "completed_steps": completed,
        "messages": [AIMessage(content=f"{status_msg}")]
    }