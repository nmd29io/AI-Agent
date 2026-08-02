from typing import TypedDict, Annotated, List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


from typing import TypedDict, List, Dict, Any, Optional


class UnderwritingState(TypedDict):
    # Input cơ bản
    company_tax_code: str
    loan_amount_requested: float
    loan_purpose: str

    # Tiến độ điều phối (Routing Management)
    next_step: Optional[str]
    completed_steps: List[str]

    # Kết quả từ các Chuyên gia (Nodes)
    cic_status: Optional[Dict[str, Any]]
    financial_ratios: Optional[Dict[str, Any]]
    legal_compliance: Optional[Dict[str, Any]]
    total_liabilities: Optional[Dict[str, Any]]

    # Kết quả Thẩm định Cuối cùng
    assessment_result: Optional[Dict[str, Any]]
    messages: List[Any]
