import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

import asyncio
from src.nodes.rag_compliance_node import rag_compliance_node

async def run_test():
    # Test case 1: Mục đích vay hợp lệ
    state_valid = {
        "loan_purpose": "Bổ sung vốn lưu động để thanh toán tiền mua nguyên vật liệu sản xuất"
    }
    # Test case 2: Vi phạm cấm cho vay (Đảo nợ)
    state_violation = {
        "loan_purpose": "Vay tiền để thanh toán khoản vay cũ và đảo nợ ngân hàng khác"
    }

    print("=== TEST CASE 1: HỢP LỆ ===")
    res1 = await rag_compliance_node(state_valid)
    print(res1["messages"][0].content)

    print("\n" + "="*50 + "\n")

    print("=== TEST CASE 2: VI PHẠM ĐẢO NỢ ===")
    res2 = await rag_compliance_node(state_violation)
    print(res2["messages"][0].content)

if __name__ == "__main__":
    asyncio.run(run_test())