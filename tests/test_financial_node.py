import sys
from pathlib import Path

# Thêm root dir vào sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

import asyncio
from src.nodes.financial_calc_node import financial_calculator_node

async def run_test():
    # Mô phỏng State chứa dữ liệu từ Node 1
    mock_state = {
        "company_tax_code": "9999999999", # MST của Beta Corp (đòn bẩy cao D/E = 5.0)
        "cic_status": {
            "total_liabilities": 50_000_000_000.0,
            "owner_equity": 10_000_000_000.0,
            "ebitda": 3_000_000_000.0,
            "annual_debt_service": 4_000_000_000.0
        }
    }

    result = await financial_calculator_node(mock_state)

    print("\n=== KẾT QUẢ TÍNH TOÁN TÀI CHÍNH ===")
    print("1. Data Output:", result["financial_ratios"])
    print("\n2. UI Log Message:\n", result["messages"][0].content)

if __name__ == "__main__":
    asyncio.run(run_test())