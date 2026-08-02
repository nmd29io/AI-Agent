import asyncio
from src.nodes.cic_csv_node import cic_and_crm_csv_node

async def run_test():
    # Giả lập State đầu vào với MST có trong CSV
    mock_state = {
        "company_tax_code": "2242118695",
        "loan_amount_requested": 10_000_000_000.0,
        "loan_purpose": "Bổ sung vốn lưu động"
    }
    
    result = await cic_and_crm_csv_node(mock_state)
    
    print("\n=== KẾT QUẢ CẬP NHẬT TRONG STATE ===")
    print("1. CIC Status Data:", result["cic_status"])
    print("\n2. Log Message:\n", result["messages"][0].content)

if __name__ == "__main__":
    asyncio.run(run_test())