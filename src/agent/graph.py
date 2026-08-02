from langgraph.graph import StateGraph, START, END
from src.schemas.underwriting_state import UnderwritingState

# Import Supervisor và các Nodes
from src.nodes.supervisor_node import supervisor_node, route_next
from src.nodes.cic_csv_node import cic_csv_node
from src.nodes.financial_calc_node import financial_calculator_node
from src.nodes.rag_compliance_node import rag_compliance_node
from src.nodes.underwriting_specialist_node import underwriting_specialist_node


def build_supervisor_underwriting_graph():
    """
    Khởi tạo Workflow Thẩm định Tín dụng dạng Supervisor Multi-Agent Graph.
    """
    workflow = StateGraph(UnderwritingState)

    # 1. Đăng ký tất cả các Node
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("node_cic_crm", cic_csv_node)
    workflow.add_node("node_financial_calc", financial_calculator_node)
    workflow.add_node("node_rag_compliance", rag_compliance_node)
    workflow.add_node("node_underwriting_specialist", underwriting_specialist_node)

    # 2. Bắt đầu luồng luôn luôn từ Supervisor
    workflow.add_edge(START, "supervisor")

    # 3. Thiết lập Rẽ nhánh Điều kiện (Conditional Edges) từ Supervisor sang các Agent
    workflow.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "node_cic_crm": "node_cic_crm",
            "node_financial_calc": "node_financial_calc",
            "node_rag_compliance": "node_rag_compliance",
            "node_underwriting_specialist": "node_underwriting_specialist",
            "END": END
        }
    )

    # 4. Sau khi mỗi Chuyên gia xử lý xong ➔ Quay lại Supervisor để đánh giá tiếp
    workflow.add_edge("node_cic_crm", "supervisor")
    workflow.add_edge("node_financial_calc", "supervisor")
    workflow.add_edge("node_rag_compliance", "supervisor")
    workflow.add_edge("node_underwriting_specialist", "supervisor")

    # 5. Biên dịch Graph
    app = workflow.compile()
    return app


app = build_supervisor_underwriting_graph()