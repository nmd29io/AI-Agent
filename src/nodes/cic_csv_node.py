from typing import Dict, Any
from langchain_core.messages import AIMessage
from src.schemas.underwriting_state import UnderwritingState
from src.services.csv_banking_service import CSVBankingService

# Khởi tạo Service đọc CSV (Global Instance)
csv_banking_service = CSVBankingService(csv_file_path="data/cic_crm_database.csv")


async def cic_and_crm_csv_node(state: UnderwritingState) -> Dict[str, Any]:
    """
    Node 1: Tra cứu CIC & CRM doanh nghiệp từ file CSV CSDL.
    """
    tax_code = state.get("company_tax_code")

    if not tax_code:
        raise ValueError("Lỗi Workflow: Chưa truyền Mã số thuế (company_tax_code) vào State.")

    # Truy vấn bất đồng bộ tới CSV Service
    credit_report = await csv_banking_service.fetch_credit_report(tax_code)
    credit_data_dict = credit_report.model_dump()

    # Tạo log thông báo hiển thị cho RM Dashboard
    status_msg = (
        f"✅ **[CIC & CRM CSV Service]:** Đã tra cứu dữ liệu MST {tax_code}.\n"
        f"- **Tên doanh nghiệp:** {credit_report.company_name}\n"
        f"- **Xếp hạng nội bộ:** {credit_report.internal_rating}\n"
        f"- **Phân loại CIC:** {credit_report.debt_group} (Điểm CIC: {credit_report.credit_score})\n"
        f"- **Số lần nợ quá hạn (36M):** {credit_report.overdue_36m_count} lần\n"
        f"- **Tổng dư nợ hiện tại:** {credit_report.total_current_debt:,.0f} VNĐ"
    )

    # Cập nhật State cho LangGraph Engine
    return {
        "cic_status": credit_data_dict,
        "messages": [AIMessage(content=status_msg)]
    }
