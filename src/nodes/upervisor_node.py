from typing import Dict, Any, Literal
from src.schemas.underwriting_state import UnderwritingState

def supervisor_node(state: UnderwritingState) -> Dict[str, Any]:
    """
    Node Điều phối (Supervisor): Phân tích State hiện tại để chỉ định công việc tiếp theo.
    """
    completed = state.get("completed_steps", [])
    
    # 1. Kiểm tra Pháp lý khẩn cấp (Early Exit nếu vi phạm nghiêm trọng)
    legal_data = state.get("legal_compliance")
    if legal_data and not legal_data.get("is_compliant", True):
        # Nếu đã phát hiện vi phạm pháp lý -> Chuyển thẳng tới Báo cáo Thẩm định để Từ chối
        if "node_underwriting_specialist" not in completed:
            return {"next_step": "node_underwriting_specialist"}

    # 2. Luồng thu thập dữ liệu chuyên môn theo thứ tự
    if "node_cic_crm" not in completed:
        return {"next_step": "node_cic_crm"}
    
    if "node_financial_calc" not in completed:
        return {"next_step": "node_financial_calc"}

    if "node_rag_compliance" not in completed:
        return {"next_step": "node_rag_compliance"}

    if "node_underwriting_specialist" not in completed:
        return {"next_step": "node_underwriting_specialist"}

    # 3. Khi tất cả các bước đã hoàn thành -> Kết thúc
    return {"next_step": "END"}


def route_next(state: UnderwritingState) -> str:
    """Hàm điều hướng Conditional Edge cho LangGraph"""
    return state.get("next_step", "END")