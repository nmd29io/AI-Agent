import asyncio
import os
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, TypedDict, operator

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.nodes.rag_compliance_node import RagLegalEngine
from src.services.csv_banking_service import CSVBankingService

# Nạp biến môi trường từ .env
load_dotenv(override=True)

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

# Tối ưu CSS để không bao giờ bị cắt chữ (ellipsis ...) trên các thẻ Metric
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: unset !important;
    }
    [data-testid="stMetricValue"] > div {
        font-size: 1.12rem !important;
        white-space: normal !important;
        word-break: break-word !important;
        line-height: 1.35 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
        white-space: normal !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 2. KHỞI TẠO SERVICES
# ==========================================
@st.cache_resource
def get_banking_service():
    return CSVBankingService()


@st.cache_resource
def get_legal_engine():
    return RagLegalEngine()


banking_service = get_banking_service()
legal_engine = get_legal_engine()

# ==========================================
# 3. ĐỊNH NGHĨA SCHEMAS & STATE
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
# 4. ĐỊNH NGHĨA CÁC NODES TRONG LANGGRAPH
# ==========================================


async def cic_csv_node(state: UnderwritingState) -> Dict[str, Any]:
    """Node Tra cứu Lịch sử Tín dụng CIC/CRM từ CSDL Ngân hàng."""
    await asyncio.sleep(0.6)  # Giả lập trễ mạng
    tax_code = state.get("company_tax_code", "").strip()
    report = await banking_service.fetch_credit_report(tax_code)

    is_found = report.company_name != "Không tìm thấy doanh nghiệp"
    company_name = (
        report.company_name
        if is_found
        else state.get("company_name", "Doanh nghiệp mới")
    )

    cic_data = {
        "company_name": company_name,
        "company_tax_code": tax_code,
        "establishment_year": report.establishment_year if is_found else 2024,
        "debt_group": report.debt_group
        if is_found
        else "Nhóm 1 - Nợ chuẩn (Chưa có dư nợ CIC)",
        "credit_score": report.credit_score if is_found else 650,
        "overdue_36m_count": report.overdue_36m_count if is_found else 0,
        "total_current_debt": report.total_current_debt if is_found else 0.0,
        "internal_rating": report.internal_rating if is_found else "BBB",
        "total_liabilities": report.total_liabilities if is_found else 0.0,
        "owner_equity": report.owner_equity if is_found else 10_000_000_000.0,
        "ebitda": report.ebitda if is_found else 2_000_000_000.0,
        "annual_debt_service": report.annual_debt_service
        if is_found
        else 1_000_000_000.0,
        "is_found_in_db": is_found,
    }

    status_msg = (
        f"💳 [CIC Node]: Tra cứu thành công MST {tax_code} ({company_name}): "
        f"Nhóm nợ = {cic_data['debt_group']}, Điểm = {cic_data['credit_score']}, "
        f"Dư nợ hiện tại = {cic_data['total_current_debt']:,.0f} VNĐ"
    )

    return {
        "cic_status": cic_data,
        "company_name": company_name,
        "completed_steps": ["node_cic_crm"],
        "messages": [AIMessage(content=status_msg)],
    }


async def financial_calc_node(state: UnderwritingState) -> Dict[str, Any]:
    """Node Động cơ Tính toán Chỉ số Tài chính Python Engine."""
    await asyncio.sleep(0.6)
    cic_data = state.get("cic_status", {})
    loan_requested = float(state.get("loan_amount_requested", 0.0))

    liabilities = float(cic_data.get("total_liabilities", 0.0))
    equity = float(cic_data.get("owner_equity", 1.0))
    ebitda = float(cic_data.get("ebitda", 0.0))
    debt_service = float(cic_data.get("annual_debt_service", 1.0))

    safe_equity = equity if equity > 0 else 1.0
    safe_debt_service = debt_service if debt_service > 0 else 1.0

    # 1. Hệ số đòn bẩy hiện tại (Historical D/E)
    de_ratio = round(liabilities / safe_equity, 2)

    # 2. Hệ số đòn bẩy dự phóng sau giải ngân khoản vay (Pro-forma D/E)
    pro_forma_de = round((liabilities + loan_requested) / safe_equity, 2)

    # 3. Hạn mức cấp thêm tối đa để giữ D/E sau vay <= 2.5 (Trần hạn mức theo VCSH)
    max_safe_limit = max(0.0, round(2.5 * safe_equity - liabilities, -6))

    # 4. Khả năng trả nợ (DSCR)
    dscr = round(ebitda / safe_debt_service, 2)

    warnings = []
    if de_ratio > 2.5:
        warnings.append(
            f"CẢNH BÁO ĐỎ: Hệ số D/E hiện tại = {de_ratio} vượt ngưỡng an toàn (<= 2.5)."
        )
    if pro_forma_de > 4.0:
        warnings.append(
            f"CẢNH BÁO ĐỎ NGUY HIỂM: Số tiền xin vay ({loan_requested:,.0f} VNĐ) quá lớn so với vốn CSH ({equity:,.0f} VNĐ). Sau giải ngân, D/E dự phóng vọt lên {pro_forma_de} (vượt xa ngưỡng từ chối 4.0)!"
        )
    elif pro_forma_de > 2.5:
        warnings.append(
            f"CẢNH BÁO ĐÒN BẨY SAU VAY: Khoản vay mới đẩy D/E dự phóng lên {pro_forma_de} (vượt trần an toàn 2.5). Hạn mức tối đa an toàn khuyến nghị: {max_safe_limit:,.0f} VNĐ."
        )

    if dscr < 1.2:
        warnings.append(
            f"CẢNH BÁO ĐỎ: Hệ số DSCR = {dscr} không đủ khả năng trả nợ (>= 1.2)."
        )

    fin_ratios = {
        "de_ratio": de_ratio,
        "pro_forma_de": pro_forma_de,
        "max_safe_limit": max_safe_limit,
        "dscr": dscr,
        "warning_notes": warnings,
        "equity": equity,
        "total_liabilities": liabilities,
        "ebitda": ebitda,
        "annual_debt_service": debt_service,
    }

    return {
        "financial_ratios": fin_ratios,
        "completed_steps": ["node_financial_calc"],
        "messages": [
            AIMessage(
                content=f"📊 [Financial Node]: D/E hiện tại = {de_ratio}, D/E sau vay = {pro_forma_de}, DSCR = {dscr}. Cảnh báo: {len(warnings)}"
            )
        ],
    }


async def rag_compliance_node(state: UnderwritingState) -> Dict[str, Any]:
    """Node Tra cứu RAG Pháp lý Thông tư 39/2016/TT-NHNN."""
    await asyncio.sleep(0.5)
    loan_purpose = state.get("loan_purpose", "").strip()

    legal_check = legal_engine.check_compliance(loan_purpose)
    legal_res = legal_check.model_dump()

    return {
        "legal_compliance": legal_res,
        "completed_steps": ["node_rag_compliance"],
        "messages": [
            AIMessage(
                content=f"⚖️ [RAG Node]: Kết quả kiểm tra pháp lý = {'Tuân thủ' if legal_check.is_compliant else 'Vi phạm'}"
            )
        ],
    }


def _fallback_underwriting(state: UnderwritingState) -> Dict[str, Any]:
    """Rule-based Engine dự phòng chuẩn nghiệp vụ ngân hàng dựa trên số liệu thực tế."""
    fin = state.get("financial_ratios", {})
    cic = state.get("cic_status", {})
    legal = state.get("legal_compliance", {})

    de = fin.get("de_ratio", 0.0)
    pro_forma_de = fin.get("pro_forma_de", de)
    max_safe_limit = fin.get("max_safe_limit", 0.0)
    dscr = fin.get("dscr", 0.0)
    debt_group = str(cic.get("debt_group", ""))
    is_legal_ok = legal.get("is_compliant", True)
    loan_requested = state.get("loan_amount_requested", 0.0)
    equity = float(cic.get("owner_equity", 1.0))

    is_bad_cic = any(x in debt_group for x in ["Nhóm 3", "Nhóm 4", "Nhóm 5"])
    is_warning_cic = "Nhóm 2" in debt_group

    # 1. BẮT BUỘC TỪ CHỐI nếu vi phạm pháp lý, nợ xấu nhóm >= 3, DSCR < 1.0, hoặc D/E sau vay > 4.0
    if not is_legal_ok or de > 4.0 or pro_forma_de > 4.0 or dscr < 1.0 or is_bad_cic:
        decision = DecisionEnum.REJECT.value
        limit = 0.0
        risk = "Rất cao"
        reasons = []
        if not is_legal_ok:
            reasons.append("Mục đích vay vi phạm quy định pháp lý NHNN (Thông tư 39)")
        if is_bad_cic:
            reasons.append(f"Lịch sử tín dụng CIC xấu ({debt_group})")
        if de > 4.0:
            reasons.append(f"Đòn bẩy tài chính hiện tại quá cao (D/E = {de} > 4.0)")
        if pro_forma_de > 4.0 and de <= 4.0:
            reasons.append(
                f"Khoản vay đề nghị ({loan_requested:,.0f} VNĐ) vượt quá xa năng lực vốn CSH ({equity:,.0f} VNĐ), đẩy đòn bẩy D/E sau vay lên {pro_forma_de} (vượt ngưỡng từ chối 4.0)"
            )
        if dscr < 1.0:
            reasons.append(f"Khả năng trả nợ yếu (DSCR = {dscr} < 1.0)")
        summary = "Từ chối cấp tín dụng do: " + "; ".join(reasons) + "."

    # 2. CẦN BỔ SUNG HỒ SƠ / TÀI SẢN ĐẢM BẢO
    elif is_warning_cic or de > 2.5 or pro_forma_de > 2.5 or dscr < 1.2 or legal.get("has_warnings"):
        decision = DecisionEnum.REQUIRE_MORE_INFO.value
        # Hạn mức đề xuất bị khống chế tối đa ở mức an toàn
        limit = min(loan_requested, max_safe_limit if max_safe_limit > 0 else round(loan_requested * 0.7, -6))
        risk = "Trung bình"
        reasons = []
        if is_warning_cic:
            reasons.append(f"CIC thuộc {debt_group}")
        if de > 2.5:
            reasons.append(f"Hệ số D/E hiện tại = {de} > 2.5")
        if pro_forma_de > 2.5 and de <= 2.5:
            reasons.append(f"Khoản vay đẩy D/E sau vay lên {pro_forma_de} > 2.5")
        if dscr < 1.2:
            reasons.append(f"Hệ số DSCR = {dscr} < 1.2")
        summary = f"Cần bổ sung tài sản đảm bảo hoặc hoàn thiện hồ sơ: {'; '.join(reasons)}. Khuyến nghị khống chế trần hạn mức an toàn: {limit:,.0f} VNĐ."

    # 3. ĐỒNG Ý CẤP TÍN DỤNG
    else:
        decision = DecisionEnum.APPROVE.value
        limit = min(loan_requested, max_safe_limit if max_safe_limit > 0 else loan_requested)
        risk = "Thấp"
        summary = "Hồ sơ đáp ứng đầy đủ tiêu chuẩn tín dụng, an toàn tài chính và quy mô khoản vay hoàn toàn phù hợp với năng lực vốn chủ sở hữu."

    markdown_report = f"""# TỜ TRÌNH THẨM ĐỊNH TÍN DỤNG DOANH NGHIỆP

**Khách hàng:** {state.get('company_name', 'Doanh nghiệp')} (MST: {state.get('company_tax_code', 'N/A')})  
**Số tiền đề nghị:** `{loan_requested:,.0f} VNĐ` | **Mục đích:** {state.get('loan_purpose', 'N/A')}

---

### I. ĐỀ XUẤT PHÁN QUYẾT
* **Kết quả:** **{decision}**
* **Hạn mức đề xuất:** `{limit:,.0f} VNĐ`
* **Mức độ rủi ro:** **{risk}**

### II. ĐÁNH GIÁ CHI TIẾT
* **Lịch sử tín dụng CIC:** {cic.get('debt_group', 'N/A')} (Điểm: `{cic.get('credit_score', 0)}`, Dư nợ hiện tại: `{cic.get('total_current_debt', 0):,.0f} VNĐ`, Quá hạn 36T: `{cic.get('overdue_36m_count', 0)}` lần)
* **Đòn bẩy tài chính hiện tại (D/E):** `{de}` (Quy định: $\\le 2.5$)
* **Đòn bẩy tài chính dự phóng sau vay:** `{pro_forma_de}` (Trần an toàn: $\\le 2.5$, Ngưỡng từ chối: $> 4.0$)
* **Khả năng trả nợ (DSCR):** `{dscr}` (Quy định: $\\ge 1.2$)
* **Pháp lý NHNN:** {'✅ Tuân thủ Thông tư 39/2016/TT-NHNN' if is_legal_ok else '❌ Vi phạm quy định cấm cho vay'}

### III. TÓM TẮT LÝ DO & ĐIỀU KIỆN
{summary}
"""
    return {
        "decision": decision,
        "recommended_credit_limit": limit,
        "risk_level": risk,
        "summary_notes": summary,
        "markdown_report": markdown_report,
    }


async def underwriting_specialist_node(state: UnderwritingState) -> Dict[str, Any]:
    """Node Agent Chuyên viên Lập Tờ trình Thẩm định Tín dụng."""
    tax_code = state.get("company_tax_code", "")
    comp_name = state.get("company_name", "")
    loan_requested = state.get("loan_amount_requested", 0.0)
    loan_purpose = state.get("loan_purpose", "")

    cic = state.get("cic_status", {})
    fin = state.get("financial_ratios", {})
    legal = state.get("legal_compliance", {})

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if api_key:
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=api_key,
                temperature=0.2,
            )
            structured_llm = llm.with_structured_output(
                UnderwritingAssessmentSchema
            )

            prompt = f"""
            Bạn là Chuyên viên Thẩm định Tín dụng Doanh nghiệp Cấp cao tại Ngân hàng. Hãy phân tích hồ sơ và lập Tờ trình Thẩm định Tín dụng chi tiết:
            
            - Doanh nghiệp: {comp_name} (MST: {tax_code})
            - Vốn chủ sở hữu (VCSH): {fin.get('equity', 0):,.0f} VNĐ | EBITDA: {fin.get('ebitda', 0):,.0f} VNĐ
            - Số tiền đề nghị vay: {loan_requested:,.0f} VNĐ | Mục đích: {loan_purpose}
            - Lịch sử CIC: Nhóm nợ: {cic.get('debt_group')}, Điểm: {cic.get('credit_score')}, Dư nợ hiện tại: {cic.get('total_current_debt', 0):,.0f} VNĐ, Quá hạn 36T: {cic.get('overdue_36m_count', 0)} lần.
            - Đòn bẩy Tài chính:
              + D/E hiện tại = {fin.get('de_ratio')} (Chuẩn <= 2.5)
              + D/E dự phóng sau giải ngân khoản vay = {fin.get('pro_forma_de')} (Trần an toàn <= 2.5, Bắt buộc TỪ CHỐI nếu > 4.0)
              + Hạn mức vay an toàn tối đa theo VCSH: {fin.get('max_safe_limit', 0):,.0f} VNĐ
            - Khả năng trả nợ: Hệ số DSCR = {fin.get('dscr')} (Ngưỡng >= 1.2). Cảnh báo: {fin.get('warning_notes')}.
            - Kiểm tra Pháp lý NHNN: {'Đạt' if legal.get('is_compliant') else 'Không đạt'}. Vi phạm: {legal.get('violations', [])}. Cảnh báo: {legal.get('warnings', [])}.
            
            QUY TẮC PHÁN QUYẾT BẮT BUỘC:
            1. Bắt buộc TỪ CHỐI CẤP TÍN DỤNG: Nếu D/E dự phóng sau vay > 4.0 (khoản vay quá lớn so với vốn CSH) HOẶC D/E hiện tại > 4.0 HOẶC DSCR < 1.0 HOẶC Vi phạm pháp lý HOẶC Nhóm nợ CIC >= Nhóm 3.
            2. CẦN BỔ SUNG HỒ SƠ / TÀI SẢN ĐẢM BẢO: Nếu D/E sau vay nằm trong khoảng 2.5 - 4.0 HOẶC Nhóm nợ 2 HOẶC DSCR 1.0 - 1.2. Hạn mức đề xuất không được vượt quá hạn mức an toàn ({fin.get('max_safe_limit', 0):,.0f} VNĐ).
            3. ĐỒNG Ý CẤP TÍN DỤNG: Chỉ khi tất cả các chỉ số (kể cả D/E sau vay <= 2.5) đều đạt chuẩn.
            4. Viết Báo cáo Markdown đầy đủ các mục: I. Tóm tắt Đề xuất & Hạn mức, II. Phân tích Tài chính & Khả năng hấp thụ nợ, III. Tín nhiệm CIC & Pháp lý, IV. Kết luận & Điều kiện đi kèm.
            """

            assessment_res: UnderwritingAssessmentSchema = (
                await structured_llm.ainvoke(prompt)
            )
            result_dict = assessment_res.model_dump()
        except Exception:
            result_dict = _fallback_underwriting(state)
    else:
        result_dict = _fallback_underwriting(state)

    return {
        "assessment_result": result_dict,
        "completed_steps": ["node_underwriting_specialist"],
        "messages": [
            AIMessage(
                content=f"📝 [Specialist Node]: Đã xuất Tờ trình cho {comp_name}. Phán quyết = {result_dict['decision']}"
            )
        ],
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

SAMPLE_PROFILES = {
    "1277933982": {
        "name": "Kwinu",
        "desc": "Nhóm 1 | AAA | D/E: 1.33, DSCR: 3.12 ──► Phê duyệt Hạng AAA",
    },
    "0101234567": {
        "name": "Alpha Corp",
        "desc": "Nhóm 1 | AA | D/E: 1.75, DSCR: 2.0 ──► Phê duyệt Chuẩn",
    },
    "9853801961": {
        "name": "Voomm",
        "desc": "Nhóm 1 | A | D/E: 11.14 (Quá cao > 4.0) ──► Từ chối đòn bẩy",
    },
    "0309998887": {
        "name": "Beta Corp",
        "desc": "Nhóm 1 | BBB | D/E: 2.0, DSCR: 0.5 (< 1.0) ──► Từ chối dòng tiền",
    },
    "0128265885": {
        "name": "Gigabox",
        "desc": "Nhóm 2 | BB | D/E: 2.8, DSCR: 1.14 ──► Yêu cầu bổ sung hồ sơ / TSĐB",
    },
    "2242118695": {
        "name": "Dablist",
        "desc": "Nhóm 3 (Dưới tiêu chuẩn) | B | Quá hạn 15 lần ──► Từ chối",
    },
    "6917580190": {
        "name": "Kayveo",
        "desc": "Nhóm 4 (Nghi ngờ) | CCC | D/E: 7.33 ──► Từ chối",
    },
    "7855258141": {
        "name": "Yodoo",
        "desc": "Nhóm 5 (Mất vốn) | CCC | EBITDA âm ──► Từ chối",
    },
    "0416764972": {
        "name": "Fivespan Tech",
        "desc": "Nhóm 1 | Doanh nghiệp mới | Dư nợ CIC 0đ ──► Duyệt Start-up",
    },
    "8407952546": {
        "name": "Janyx Logistics",
        "desc": "Nhóm 1 | A | D/E: 2.6 (Ranh giới), DSCR: 1.25 ──► Cân nhắc phê duyệt",
    },
}

sample_options = ["-- Tùy chỉnh / Nhập tự do --"] + [
    f"{mst} - {v['name']} ({v['desc']})" for mst, v in SAMPLE_PROFILES.items()
]

# Khởi tạo giá trị ban đầu trong session_state nếu chưa có
if "tax_code_input" not in st.session_state:
    st.session_state["tax_code_input"] = "1277933982"

if "comp_name_input" not in st.session_state:
    st.session_state["comp_name_input"] = "Kwinu"

if "selected_sample_key" not in st.session_state:
    st.session_state["selected_sample_key"] = sample_options[1]


def on_sample_change():
    """Tự động cập nhật ô Mã CIF/MST và Tên Doanh nghiệp khi chọn từ dropdown."""
    selected = st.session_state.get("selected_sample_key")
    if selected and selected != "-- Tùy chỉnh / Nhập tự do --":
        mst = selected.split(" - ")[0].strip()
        st.session_state["tax_code_input"] = mst
        comp = banking_service.get_company_by_tax_code(mst)
        if comp:
            st.session_state["comp_name_input"] = str(comp.get("company_name", ""))


def on_tax_code_change():
    """Tự động tra cứu Tên Doanh nghiệp và đồng bộ dropdown khi người dùng gõ MST."""
    current_mst = st.session_state.get("tax_code_input", "").strip()
    st.session_state["tax_code_input"] = current_mst
    comp = banking_service.get_company_by_tax_code(current_mst)
    if comp:
        st.session_state["comp_name_input"] = str(comp.get("company_name", ""))
    
    # Đồng bộ ngược lại dropdown nếu MST này thuộc danh sách mẫu
    matched_opt = "-- Tùy chỉnh / Nhập tự do --"
    for opt in sample_options:
        if opt.startswith(current_mst + " - "):
            matched_opt = opt
            break
    st.session_state["selected_sample_key"] = matched_opt


with st.sidebar:
    st.header("📋 Hồ sơ Khách hàng Vay")

    selected_sample = st.selectbox(
        "💡 Chọn nhanh hồ sơ mẫu từ CSDL:",
        options=sample_options,
        key="selected_sample_key",
        on_change=on_sample_change,
    )

    tax_code = st.text_input(
        "Mã CIF / Mã số thuế (MST) Doanh nghiệp",
        key="tax_code_input",
        on_change=on_tax_code_change,
        help="Nhập MST (10 chữ số) hoặc chọn từ danh sách mẫu ở trên.",
    ).strip()

    # Tra cứu thông tin từ CSDL CSV đồng bộ ngay khi người dùng gõ hoặc chọn MST
    comp_info = banking_service.get_company_by_tax_code(tax_code)

    if comp_info:
        auto_comp_name = str(comp_info.get("company_name", ""))
        st.success(
            f"✅ **Đã tìm thấy trong CSDL Ngân hàng:**\n\n"
            f"- **DN:** **{auto_comp_name}**\n"
            f"- **Năm TL:** `{comp_info.get('establishment_year')}` | **Xếp hạng:** `{comp_info.get('internal_rating')}`\n"
            f"- **CIC:** `{comp_info.get('debt_group')}`\n"
            f"- **Điểm CIC:** `{comp_info.get('credit_score')}` | **Dư nợ:** `{float(comp_info.get('total_current_debt', 0)):,.0f} VNĐ`"
        )
    else:
        st.info(
            "ℹ️ MST chưa có trong CSDL nội bộ. Hệ thống sẽ thẩm định theo thông tin nhập tay."
        )

    company_name = st.text_input(
        "Tên Doanh nghiệp",
        key="comp_name_input",
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
    btn_start = st.button(
        "🚀 Bắt đầu Thẩm định AI", type="primary", use_container_width=True
    )

# Main UI Tabs
tab_report, tab_graph, tab_raw = st.tabs(
    ["📄 Tờ trình Thẩm định", "🌐 Tiến trình Multi-Agent", "🔍 Dữ liệu Thô (State)"]
)

# Kiểm tra xem kết quả hiện có trong session_state có phải của MST hiện tại hay không
evaluated_tax_code = st.session_state.get("evaluated_tax_code")
evaluated_comp_name = st.session_state.get("evaluated_company_name")
has_tax_code_changed = (
    "final_state" in st.session_state and evaluated_tax_code != tax_code
)

if has_tax_code_changed:
    st.warning(
        f"⚠️ **Thông tin CIF/MST đã thay đổi!**\n\n"
        f"- Báo cáo hiển thị bên dưới hiện là kết quả của MST cũ: **{evaluated_tax_code}** ({evaluated_comp_name}).\n"
        f"- Bạn vừa nhập MST mới: **{tax_code}** ({company_name}).\n\n"
        f"👉 Hãy bấm **'🚀 Bắt đầu Thẩm định AI'** ở thanh bên trái để tính toán lại số liệu cho doanh nghiệp mới này!"
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

    status_box = st.status(
        f"🤖 Đang thẩm định hồ sơ: {company_name} (MST: {tax_code})...",
        expanded=True,
    )

    async def run_pipeline():
        current_state = initial_state
        async for event in app_graph.astream(initial_state):
            for node_name, updated_dict in event.items():
                if node_name == "supervisor_node":
                    status_box.write(
                        f"👔 **[Supervisor]**: Điều hướng tiếp theo ➔ `{updated_dict.get('next_node')}`"
                    )
                elif node_name == "node_cic_crm":
                    status_box.write(
                        f"💳 **[CIC Node]**: Đã hoàn tất tra cứu CSDL CIC/CRM cho MST `{tax_code}`."
                    )
                elif node_name == "node_financial_calc":
                    fin = updated_dict.get("financial_ratios", {})
                    status_box.write(
                        f"📊 **[Financial Engine]**: Đã tính toán D/E = `{fin.get('de_ratio')}`, DSCR = `{fin.get('dscr')}`."
                    )
                elif node_name == "node_rag_compliance":
                    status_box.write(
                        "⚖️ **[RAG Node]**: Đã đối chiếu Thông tư 39/2016/TT-NHNN."
                    )
                elif node_name == "node_underwriting_specialist":
                    status_box.write(
                        "📝 **[Specialist Agent]**: Đã lập xong Tờ trình Thẩm định Tín dụng."
                    )

                # Merge state
                for k, v in updated_dict.items():
                    if k in ["completed_steps", "messages"]:
                        current_state[k] = current_state.get(k, []) + v
                    else:
                        current_state[k] = v

        status_box.update(
            label=f"✅ Thẩm định hoàn tất cho {company_name} (MST: {tax_code})!",
            state="complete",
            expanded=False,
        )
        return current_state

    # Khởi chạy pipeline bất đồng bộ
    final_state = asyncio.run(run_pipeline())
    st.session_state["final_state"] = final_state
    st.session_state["evaluated_tax_code"] = tax_code
    st.session_state["evaluated_company_name"] = company_name
    st.rerun()

# Hiển thị Kết quả nếu đã có dữ liệu trong Session State
if "final_state" in st.session_state:
    state = st.session_state["final_state"]
    assessment = state.get("assessment_result", {})
    cic = state.get("cic_status", {})
    fin = state.get("financial_ratios", {})

    with tab_report:
        st.subheader(
            f"📄 Tờ trình Thẩm định: {state.get('company_name')} (MST: {state.get('company_tax_code')})"
        )

        # 5 Top Metrics với tỷ lệ cột ưu tiên độ rộng cho Phán quyết
        m1, m2, m3, m4, m5 = st.columns([1.8, 1.3, 1.0, 0.9, 0.9])
        raw_decision = assessment.get("decision", "N/A")
        decision_str = str(
            raw_decision.value if hasattr(raw_decision, "value") else raw_decision
        )

        if "ĐỒNG Ý" in decision_str.upper() or "APPROVE" in decision_str.upper():
            display_decision = "ĐỒNG Ý CẤP TÍN DỤNG"
            delta_label = "CHẤP THUẬN"
            delta_style = "normal"
        elif (
            "BỔ SUNG" in decision_str.upper()
            or "MORE_INFO" in decision_str.upper()
            or "REQUIRE" in decision_str.upper()
        ):
            display_decision = "CẦN BỔ SUNG HỒ SƠ"
            delta_label = "YÊU CẦU TSĐB"
            delta_style = "off"
        else:
            display_decision = "TỪ CHỐI CẤP TÍN DỤNG"
            delta_label = "TỪ CHỐI"
            delta_style = "inverse"

        m1.metric("Quyết định", display_decision, delta=delta_label, delta_color=delta_style)

        m2.metric(
            "Hạn mức Đề xuất",
            f"{assessment.get('recommended_credit_limit', 0):,.0f} VNĐ",
        )
        m3.metric("Mức độ Rủi ro", assessment.get("risk_level", "N/A"))

        de_val = fin.get("de_ratio", 0.0)
        pro_forma_de = fin.get("pro_forma_de", de_val)
        dscr_val = fin.get("dscr", 0.0)
        m4.metric(
            "Đòn bẩy D/E (Sau vay)",
            f"{pro_forma_de}",
            delta=f"Hiện tại: {de_val} (Chuẩn ≤ 2.5)" if pro_forma_de <= 2.5 else f"Vượt trần (Cũ: {de_val})",
            delta_color="normal" if pro_forma_de <= 2.5 else "inverse",
        )
        m5.metric(
            "Trả nợ DSCR",
            f"{dscr_val}",
            delta="Chuẩn >= 1.2" if dscr_val >= 1.2 else "Dưới chuẩn < 1.2",
            delta_color="normal" if dscr_val >= 1.2 else "inverse",
        )

        # Thẻ thông tin chi tiết CIC & BCTC
        with st.expander(
            "💳 Chi tiết Lịch sử Tín dụng CIC & Báo cáo Tài chính trích xuất",
            expanded=False,
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"**Phân loại CIC:** `{cic.get('debt_group', 'N/A')}`")
            c2.write(f"**Điểm tín dụng:** `{cic.get('credit_score', 'N/A')}`")
            c3.write(
                f"**Quá hạn 36 tháng:** `{cic.get('overdue_36m_count', 0)} lần`"
            )
            c4.write(
                f"**Tổng dư nợ:** `{float(cic.get('total_current_debt', 0)):,.0f} VNĐ`"
            )

            f1, f2, f3, f4 = st.columns(4)
            f1.write(
                f"**Nợ phải trả:** `{float(cic.get('total_liabilities', 0)):,.0f} VNĐ`"
            )
            f2.write(
                f"**Vốn CSH:** `{float(cic.get('owner_equity', 0)):,.0f} VNĐ`"
            )
            f3.write(
                f"**EBITDA:** `{float(cic.get('ebitda', 0)):,.0f} VNĐ`"
            )
            f4.write(
                f"**Nghĩa vụ nợ/năm:** `{float(cic.get('annual_debt_service', 0)):,.0f} VNĐ`"
            )

            p1, p2 = st.columns(2)
            p1.write(
                f"**D/E hiện tại:** `{de_val}` ➔ **D/E sau vay:** `{pro_forma_de}` (Chuẩn: `≤ 2.5` | Ngưỡng từ chối: `> 4.0`)"
            )
            max_safe = fin.get("max_safe_limit", 0.0)
            p2.write(
                f"**Trần hạn mức an toàn tối đa:** `{max_safe:,.0f} VNĐ`"
            )

        st.markdown("---")

        # Markdown Report Output
        st.markdown(assessment.get("markdown_report", "Không có báo cáo."))

    with tab_graph:
        st.subheader(
            f"Bản đồ Tiến trình Multi-Agent ({state.get('company_name')})"
        )
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
        st.info(
            "👈 Hãy nhấn nút **'🚀 Bắt đầu Thẩm định AI'** ở thanh bên trái để khởi chạy hệ thống."
        )