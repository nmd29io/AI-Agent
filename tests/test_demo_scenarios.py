import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

import asyncio
from dotenv import load_dotenv

# Load env variables
load_dotenv(override=True)

from src.graph import app

# Danh sách 3 Kịch bản Demo
DEMO_SCENARIOS = [
    {
        "scenario_name": "KỊCH BẢN 1: Alpha Corp - Hồ sơ Đủ điều kiện (Chuẩn)",
        "input": {
            "company_tax_code": "0101234567",
            "loan_amount_requested": 8_000_000_000.0,
            "loan_purpose": "Bổ sung vốn lưu động mua nguyên vật liệu sản xuất hạt nhựa",
        }
    },
    {
        "scenario_name": "KỊCH BẢN 2: Beta Corp - Rủi ro Đòn bẩy cao & DSCR Yếu",
        "input": {
            "company_tax_code": "0207654321",
            "loan_amount_requested": 15_000_000_000.0,
            "loan_purpose": "Mở rộng xưởng sản xuất và mua máy móc thiết bị mới",
        }
    },
    {
        "scenario_name": "KỊCH BẢN 3: Gamma Corp - Vi phạm Quy định Pháp lý (Đảo nợ / BĐS)",
        "input": {
            "company_tax_code": "0309998887",
            "loan_amount_requested": 10_000_000_000.0,
            "loan_purpose": "Vay vốn để cơ cấu lại nợ và đảo nợ ngân hàng khác",
        }
    }
]

async def run_demo():
    for case in DEMO_SCENARIOS:
        print("\n" + "="*80)
        print(f"🚀 {case['scenario_name']}")
        print("="*80)
        
        # Chạy pipeline
        final_state = await app.ainvoke(case["input"])
        assessment = final_state.get("assessment_result", {})
        
        print(f"\n📌 QUYẾT ĐỊNH PHÁN QUYẾT : {assessment.get('decision')}")
        print(f"💰 HẠN MỨC ĐỀ XUẤT     : {assessment.get('recommended_credit_limit', 0):,.0f} VNĐ")
        print(f"⚠️ MỨC ĐỘ RỦI RO       : {assessment.get('risk_level')}")
        
        if assessment.get("key_risks"):
            print("\n🚨 CÁC RỦI RO CHÍNH PHÁT HIỆN:")
            for risk in assessment.get("key_risks", []):
                print(f"  - {risk}")
                
        print("\n" + "-"*80)

if __name__ == "__main__":
    asyncio.run(run_demo()) 