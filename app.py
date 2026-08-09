import asyncio
import os
from enum import Enum
from typing import Annotated, Any, Dict, List, TypedDict, operator

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

# Nạp biến môi trường từ .env
load_dotenv()

# ==========================================
# 1. CẤU HÌNH TRANG STREAMLIT
# ==========================================
st.set_page_config(
    page_title="AI Banking Copilot - Thẩm định Tín dụng Doanh nghiệp",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏦 AI Banking Copilot - Thẩm định Tín dụng Doanh nghiệp")
st.caption(
    "Hệ thống Multi-Agent tự động hóa quy trình tra cứu CIC, phân tích BCTC và rà soát pháp lý bằng LangGraph."
)

# ==========================================
# 2. ĐỊNH NGHĨA SCHEMAS & STATE
# ==========================================


class DecisionEnum(str, Enum):
    APPROVE = "ĐỒNG Ý CẤP TÍN DỤNG"
    REJECT = "TỪ CHỐI CẤP TÍN DỤNG"
    REQUIRE_MORE_INFO = "CẦN BỔ SUNG HỒ SƠ"


class UnderwritingAssessmentSchema(BaseModel):
    decision: DecisionEnum = Field(description="Quyết định cấp tín dụng cuối cùng")
    recommended_credit_limit: float = Field(
        description="Hạn mức phê duyệt đề xuất (VNĐ)"
    )
    risk_level: str = Field(
        description="Mức độ rủi ro (Thấp, Trung bình, Cao, Rất cao)"
    )
    summary_notes: str = Field(
        description="Tóm tắt lý do chính cho phán quyết"
    )
    markdown_report: str = Field(
        description="Toàn bộ Tờ trình Thẩm định Tín dụng dạng Markdown"
    )


class UnderwritingState(TypedDict):
    company_tax_code: str
    company_name: str
    loan_amount_requested: float
    loan_purpose: str

    # Dữ liệu kết quả từ các Node
    cic_status: Dict[str, Any]
    financial_ratios: Dict[str, Any]
    legal_compliance: Dict[str, Any]
    assessment_result: Dict[str, Any]

    # Quản lý luồng thực thi
    completed_steps: Annotated[List[str], operator.add]
    next_node: str
    messages: Annotated[List[BaseMessage], operator.add]


# ==========================================
# 3. MOCK DATA & MÔ PHỎNG DATABASE
# ==========================================
def get_mock_database(tax_code: str):
    """Giả lập cơ sở dữ liệu doanh nghiệp từ CSDL Ngân hàng."""
    return {
        "company_tax_code": tax_code,
        "company_name": "Công ty TNHH Sản xuất & Thương mại Voomm",
        "cic_data": {
            "debt_group": "Nhóm 1 (Nợ đủ tiêu chuẩn)",
            "credit_score": 849,
            "overdue_36m_count": 0,
            "total_current_debt": 303_450_000_000.0,
        },
        "financial_raw": {
            "total_assets": 450_000_000_000.0,
            "total_liabilities": 390_000_000_000.0,
            "equity": 34_500_000_000.0,
            "ebitda": 15_000_000_000.0,
            "debt_service": 16_800_000_000.0,
        },
    }


# ==========================================
# 4. ĐỊNH NGHĨA CÁC NODES TRONG LANGGRAPH
# ==========================================


async def cic_csv_node(state: UnderwritingState) -> Dict[str, Any]:
    """Node Tra cứu Lịch sử Tín dụng CIC/CRM."""
    await asyncio.sleep(1.0)  # Giả lập trễ mạng
    db = get_mock_database(state["company_tax_code"])
    cic_data = db["cic_data"]

    return {
        "cic_status": cic_data,
        "completed_steps": ["node_cic_crm"],
        "messages": [
            AIMessage(
                content=f"💳 [CIC Node]: Trích xuất thành công: Nhóm nợ = {cic_data['debt_group']}, Điểm = {cic_data['credit_score']}"
            )
        ],
    }


async def financial_calc_node(state: UnderwritingState) -> Dict[str, Any]:
    """Node Động cơ Tính toán Chỉ số Tài chính Python Engine."""
    await asyncio.sleep(1.2)
    db = get_mock_database(state["company_tax_code"])
    raw_fin = db["financial_raw"]

    liabilities = raw_fin["total_liabilities"]
    equity = raw_fin["equity"]
    ebitda = raw_fin["ebitda"]
    debt_service = raw_fin["debt_service"]

    # Tính toán chính xác bằng Python
    de_ratio = round(liabilities / equity, 2) if equity > 0 else 999.0
    dscr = round(ebitda / debt_service, 2) if debt_service > 0 else 0.0

    warnings = []
    if de_ratio > 2.5:
        warnings.append(
            f"CẢNH BÁO ĐỎ: Hệ số D/E = {de_ratio} vượt ngưỡng an toàn (2.5)."
        )
    if dscr < 1.2:
        warnings.append(
            f"CẢNH BÁO ĐỎ: Hệ số DSCR = {dscr} không đủ khả năng trả nợ (< 1.2)."
        )

    fin_ratios = {
        "de_ratio": de_ratio,
        "dscr": dscr,
        "warning_notes": warnings,
        "equity": equity,
        "total_liabilities": liabilities,
    }

    return {
        "financial_ratios": fin_ratios,
        "completed_steps": ["node_financial_calc"],
        "messages": [
            AIMessage(
                content=f"📊 [Financial Node]: D/E = {de_ratio}, DSCR = {dscr}. Số cảnh báo: {len(warnings)}"
            )
        ],
    }


async def rag_compliance_node(state: UnderwritingState) -> Dict[str, Any]:
    """Node Tra cứu RAG Pháp lý Thông tư 39/2016/TT-NHNN."""
    await asyncio.sleep(1.0)
    loan_purpose = state.get("loan_purpose", "")

    # Giả lập đối chiếu RAG
    forbidden_terms = ["chứng khoán", "bất động sản rủi ro", "đầu cơ"]
    is_compliant = not any(term in loan_purpose.lower() for term in forbidden_terms)

    legal_res = {
        "is_compliant": is_compliant,
        "checked_regulations": ["Thông tư 39/2016/TT-NHNN"],
        "violations": (
            []
            if is_compliant
            else ["Mục đích vay nằm trong danh mục cấm/kiểm soát rủi ro."]
        ),
    }

    return {
        "legal_compliance": legal_res,
        "completed_steps": ["node_rag_compliance"],
        "messages": [
            AIMessage(
                content=f"⚖️ [RAG Node]: Kết quả kiểm tra pháp lý = {'Tuân thủ' if is_compliant else 'Vi phạm'}"
            )
        ],
    }


async def underwriting_specialist_node(state: UnderwritingState) -> Dict[str, Any]:
    """Node Agent Chuyên viên Lập Tờ trình Thẩm định Tín dụng."""
    tax_code = state["company_tax_code"]
    comp_name = state["company_name"]
    loan_requested = state["loan_amount_requested"]
    loan_purpose = state["loan_purpose"]

    cic = state.get("cic_status", {})
    fin = state.get("financial_ratios", {})
    legal = state.get("legal_compliance", {})

    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash", temperature=0.2
            )
            structured_llm = llm.with_structured_output(
                UnderwritingAssessmentSchema
            )

            prompt = f"""
            Bạn là Chuyên viên Thẩm định Tín dụng Doanh nghiệp Cấp cao. Hãy phân tích hồ sơ và lập Tờ trình Thẩm định Tín dụng chi tiết:
            
            - Doanh nghiệp: {comp_name} (MST: {tax_code})
            - Số tiền đề nghị vay: {loan_requested:,.0f} VNĐ | Mục đích: {loan_purpose}
            - Lịch sử CIC: Nhóm nợ: {cic.get('debt_group')}, Điểm: {cic.get('credit_score')}, Dư nợ hiện tại: {cic.get('total_current_debt', 0):,.0f} VNĐ.
            - Sức khỏe Tài chính: Hệ số D/E = {fin.get('de_ratio')} (Ngưỡng <= 2.5), Hệ số DSCR = {fin.get('dscr')} (Ngưỡng >= 1.2). Cảnh báo: {fin.get('warning_notes')}.
            - Kiểm tra Pháp lý NHNN: {'Đạt' if legal.get('is_compliant') else 'Không đạt'}.
            
            QUY TẮC PHÁN QUYẾT:
            1. Bắt buộc TỪ CHỐI nếu D/E > 4.0 HOẶC DSCR < 1.0 HOẶC Vi phạm pháp lý.
            2. Nếu có rủi ro nhưng chấp nhận được -> Yêu cầu bổ sung tài sản đảm bảo.
            3. Viết Báo cáo Markdown đầy đủ các mục: I. Tóm tắt Đề xuất, II. Phân tích Tài chính & Dòng tiền, III. Tín nhiệm CIC & Pháp lý, IV. Kết luận & Điều kiện đi kèm.
            """

            assessment_res: UnderwritingAssessmentSchema = (
                await structured_llm.ainvoke(prompt)
            )
            result_dict = assessment_res.model_dump()
        except Exception as e:
            st.error(f"Lỗi khi gọi Gemini API: {e}. Hệ thống sẽ sử dụng Logic Dự phòng.")
            result_dict = _fallback_underwriting(state)
    else:
        # Dự phòng khi chưa cài GEMINI_API_KEY
        result_dict = _fallback_underwriting(state)

    return {
        "assessment_result": result_dict,
        "completed_steps": ["node_underwriting_specialist"],
        "messages": [
            AIMessage(
                content=f"📝 [Specialist Node]: Đã xuất Tờ trình. Phán quyết = {result_dict['decision']}"
            )
        ],
    }


def _fallback_underwriting(state: UnderwritingState) -> Dict[str, Any]:
    """Rule-based Engine dự phòng khi không gọi được LLM."""
    fin = state.get("financial_ratios", {})
    de = fin.get("de_ratio", 0)
    dscr = fin.get("dscr", 0)

    if de > 2.5 or dscr < 1.2:
        decision = DecisionEnum.REJECT.value
        limit = 0.0
        risk = "Rất cao"
        summary = f"Doanh nghiệp vi phạm tiêu chuẩn an toàn tài chính (D/E = {de} > 2.5, DSCR = {dscr} < 1.2)."
    else:
        decision = DecisionEnum.APPROVE.value
        limit = state["loan_amount_requested"]
        risk = "Thấp"
        summary = "Hồ sơ đáp ứng đầy đủ tiêu chuẩn tín dụng và an toàn tài chính."

    markdown_report = f"""# TỜ TRÌNH THẨM ĐỊNH TÍN DỤNG DOANH NGHIỆP

**Khách hàng:** {state['company_name']} (MST: {state['company_tax_code']})

---

### I. ĐỀ XUẤT PHÁN QUYẾT
* **Kết quả:** **{decision}**
* **Hạn mức đề xuất:** `{limit:,.0f} VNĐ`
* **Mức độ rủi ro:** **{risk}**

### II. ĐÁNH GIÁ CHI TIẾT
* **Đòn bẩy tài chính (D/E):** `{de}` (Quy định: $\le 2.5$)
* **Khả năng trả nợ (DSCR):** `{dscr}` (Quy định: $\ge 1.2$)
* **Pháp lý NHNN:** Tuân thủ Thông tư 39/2016/TT-NHNN

### III. TÓM TẮT LÝ DO
{summary}
"""
    return {
        "decision": decision,
        "recommended_credit_limit": limit,
        "risk_level": risk,
        "summary_notes": summary,
        "markdown_report": markdown_report,
    }


def supervisor_node(state: UnderwritingState) -> Dict[str, Any]:
    """Supervisor Agent điều phối luồng thực thi động."""
    completed = state.get("completed_steps", [])

    if "node_cic_crm" not in completed:
        return {"next_node": "node_cic_crm"}
    if "node_financial_calc" not in completed:
        return {"next_node": "node_financial_calc"}
    if "node_rag_compliance" not in completed:
        return {"next_node": "node_rag_compliance"}
    if "node_underwriting_specialist" not in completed:
        return {"next_node": "node_underwriting_specialist"}

    return {"next_node": "__end__"}


# ==========================================
# 5. DỰNG GRAPH LANGGRAPH
# ==========================================
@st.cache_resource
def build_graph():
    workflow = StateGraph(UnderwritingState)

    workflow.add_node("supervisor_node", supervisor_node)
    workflow.add_node("node_cic_crm", cic_csv_node)
    workflow.add_node("node_financial_calc", financial_calc_node)
    workflow.add_node("node_rag_compliance", rag_compliance_node)
    workflow.add_node("node_underwriting_specialist", underwriting_specialist_node)

    workflow.set_entry_point("supervisor_node")

    workflow.add_conditional_edges(
        "supervisor_node",
        lambda state: state.get("next_node"),
        {
            "node_cic_crm": "node_cic_crm",
            "node_financial_calc": "node_financial_calc",
            "node_rag_compliance": "node_rag_compliance",
            "node_underwriting_specialist": "node_underwriting_specialist",
            "__end__": END,
        },
    )

    workflow.add_edge("node_cic_crm", "supervisor_node")
    workflow.add_edge("node_financial_calc", "supervisor_node")
    workflow.add_edge("node_rag_compliance", "supervisor_node")
    workflow.add_edge("node_underwriting_specialist", END)

    return workflow.compile()


app_graph = build_graph()

# ==========================================
# 6. GIAO DIỆN STREAMLIT (UI)
# ==========================================

# Sidebar Inputs
with st.sidebar:
    st.header("📋 Hồ sơ Khách hàng Vay")

    tax_code = st.text_input("Mã số thuế Doanh nghiệp", value="9853801961")
    company_name = st.text_input(
        "Tên Doanh nghiệp", value="Công ty TNHH Sản xuất & Thương mại Voomm"
    )
    loan_amount = st.number_input(
        "Số tiền đề nghị vay (VNĐ)",
        min_value=100_000_000,
        max_value=100_000_000_000,
        value=8_000_000_000,
        step=500_000_000,
    )
    loan_purpose = st.text_area(
        "Mục đích sử dụng vốn",
        value="Bổ sung vốn lưu động lưu thông vật tư nguyên vật liệu sản xuất kỳ III/2026",
    )

    st.markdown("---")
    btn_start = st.button("🚀 Bắt đầu Thẩm định AI", type="primary", use_container_width=True)

# Main UI Tabs
tab_report, tab_graph, tab_raw = st.tabs(
    ["📄 Tờ trình Thẩm định", "🌐 Tiến trình Multi-Agent", "🔍 Dữ liệu Thô (State)"]
)

if btn_start:
    # Khởi tạo State ban đầu
    initial_state: UnderwritingState = {
        "company_tax_code": tax_code,
        "company_name": company_name,
        "loan_amount_requested": loan_amount,
        "loan_purpose": loan_purpose,
        "cic_status": {},
        "financial_ratios": {},
        "legal_compliance": {},
        "assessment_result": {},
        "completed_steps": [],
        "next_node": "supervisor_node",
        "messages": [],
    }

    status_box = st.status("🤖 Hệ thống AI Multi-Agent đang xử lý...", expanded=True)

    async def run_pipeline():
        current_state = initial_state
        async for event in app_graph.astream(initial_state):
            for node_name, updated_dict in event.items():
                if node_name == "supervisor_node":
                    status_box.write(
                        f"👔 **[Supervisor]**: Điều hướng tiếp theo ➔ `{updated_dict.get('next_node')}`"
                    )
                elif node_name == "node_cic_crm":
                    status_box.write("💳 **[CIC Node]**: Đã hoàn tất tra cứu điểm tín dụng & lịch sử quá hạn.")
                elif node_name == "node_financial_calc":
                    status_box.write("📊 **[Financial Engine]**: Đã hoàn thành tính toán chỉ số D/E, DSCR.")
                elif node_name == "node_rag_compliance":
                    status_box.write("⚖️ **[RAG Node]**: Đã đối chiếu xong Thông tư 39/2016/TT-NHNN.")
                elif node_name == "node_underwriting_specialist":
                    status_box.write("📝 **[Specialist Agent]**: Đã lập xong Tờ trình Thẩm định Tín dụng.")

                # Merge state
                for k, v in updated_dict.items():
                    if k in ["completed_steps", "messages"]:
                        current_state[k] = current_state.get(k, []) + v
                    else:
                        current_state[k] = v

        status_box.update(
            label="✅ Thẩm định hoàn tất thành công!", state="complete", expanded=False
        )
        return current_state

    # Khởi chạy pipeline bất đồng bộ
    final_state = asyncio.run(run_pipeline())
    st.session_state["final_state"] = final_state

# Hiển thị Kết quả nếu đã có dữ liệu trong Session State
if "final_state" in st.session_state:
    state = st.session_state["final_state"]
    assessment = state.get("assessment_result", {})

    with tab_report:
        # Top Metrics
        m1, m2, m3, m4 = st.columns(4)
        decision = assessment.get("decision", "N/A")
        
        if decision == DecisionEnum.APPROVE.value:
            m1.metric("Quyết định", decision, delta="CHẤP THUẬN", delta_color="normal")
        else:
            m1.metric("Quyết định", decision, delta="TỪ CHỐI", delta_color="inverse")

        m2.metric(
            "Hạn mức Đề xuất",
            f"{assessment.get('recommended_credit_limit', 0):,.0f} VNĐ",
        )
        m3.metric("Mức độ Rủi ro", assessment.get("risk_level", "N/A"))
        
        fin = state.get("financial_ratios", {})
        m4.metric("Đòn bẩy D/E", f"{fin.get('de_ratio', 0)}", delta="Ngưỡng <= 2.5", delta_color="off")

        st.markdown("---")

        # Markdown Report Output
        st.markdown(assessment.get("markdown_report", "Không có báo cáo."))

    with tab_graph:
        st.subheader("Bản đồ Tiến trình Multi-Agent")
        st.info("Các Agent đã thực thi theo mô hình Supervisor Pattern:")

        steps = state.get("completed_steps", [])
        df_steps = pd.DataFrame(
            {
                "Bước": [i + 1 for i in range(len(steps))],
                "Nút thực thi (Node)": steps,
                "Trạng thái": ["HOÀN THÀNH"] * len(steps),
            }
        )
        st.dataframe(df_steps, use_container_width=True)

    with tab_raw:
        st.subheader("Chi tiết Trạng thái Dữ liệu (UnderwritingState)")
        st.json(state)
else:
    with tab_report:
        st.info("👈 Hãy nhấn nút **'🚀 Bắt đầu Thẩm định AI'** ở thanh bên trái để khởi chạy hệ thống.")