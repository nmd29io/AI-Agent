from langgraph.graph import StateGraph, START, END
from src.schemas.underwriting_state import UnderwritingState

# Import 4 Nodes đã xây dựng
from src.nodes.cic_csv_node import cic_csv_node
from src.nodes.financial_calc_node import financial_calculator_node
from src.nodes.rag_compliance_node import rag_compliance_node
from src.nodes.underwriting_specialist_node import underwriting_specialist_node


def build_underwriting_graph():
    """
    Hàm khởi tạo và đóng gói luồng StateGraph cho AI Agent Thẩm định Tín dụng.
    Luồng thực thi: START ➔ Node 1 (CIC) ➔ Node 2 (Financial) ➔ Node 3 (RAG) ➔ Node 4 (LLM Underwriter) ➔ END
    """
    # 1. Khởi tạo StateGraph với State dùng chung
    workflow = StateGraph(UnderwritingState)

    # 2. Đăng ký các Node vào Workflow
    workflow.add_node("node_cic_crm", cic_csv_node)
    workflow.add_node("node_financial_calc", financial_calculator_node)
    workflow.add_node("node_rag_compliance", rag_compliance_node)
    workflow.add_node("node_underwriting_specialist", underwriting_specialist_node)

    # 3. Thiết lập Luồng di chuyển (Edges)
    workflow.add_edge(START, "node_cic_crm")
    workflow.add_edge("node_cic_crm", "node_financial_calc")
    workflow.add_edge("node_financial_calc", "node_rag_compliance")
    workflow.add_edge("node_rag_compliance", "node_underwriting_specialist")
    workflow.add_edge("node_underwriting_specialist", END)

    # 4. Biên dịch (Compile) Graph
    app = workflow.compile()
    return app


# Khởi tạo instance app sẵn sàng để import sử dụng ở UI / API
app = build_underwriting_graph()