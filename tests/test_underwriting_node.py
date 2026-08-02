import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

import asyncio
from src.nodes.underwriting_specialist_node import underwriting_specialist_node

async def run_test():
    # Mô phỏng State đã chạy qua Node 1, 2, 3 với kết quả tốt (Alpha Corp)
    mock_state_approved = {
        "company_tax_code": "0101234567",
        "loan_amount_requested": 10_000_000_000.0,
        "loan_purpose": "Bổ sung vốn lưu động mua nguyên vật liệu sản xuất",
        "cic_status": {
            "company_name": "Công ty Cổ phần Tập đoàn Alpha",
            "debt_group": "Nhóm 1 - Nợ chuẩn",
            "credit_score": 725,
            "overdue_36m_count": 0,
            "total_current_debt": 15_000_000_000.0
        },
        "financial_ratios": {
            "de_ratio": 1.5,
            "dscr": 3.2,
            "de_benchmark": 2.5,
            "dscr_benchmark": 1.2,
            "warning_notes": []
        },
        "legal_compliance": {
            "is_compliant": True,
            "violations": [],
            "warnings": []
        }
    }

    print("=== THỰC THI NODE 4 (UNDERWRITING SPECIALIST) ===")
    result = await underwriting_specialist_node(mock_state_approved)
    
    print(result["messages"][0].content)
    print("\n--- NỘI DUNG TỜ TRÌNH MARKDOWN GENERATED ---")
    print(result["assessment_result"]["submission_report_markdown"])

if __name__ == "__main__":
    asyncio.run(run_test())