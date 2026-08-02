import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)

from src.agent.graph import app

async def run_supervisor_test():
    print("🚀 --- KIỂM THỬ SUPERVISOR MULTI-AGENT GRAPH --- 🚀\n")

    initial_input = {
        "company_tax_code": "0309998887", # Công ty Gamma (Vi phạm pháp lý)
        "loan_amount_requested": 10_000_000_000.0,
        "loan_purpose": "Vay vốn để đảo nợ ngân hàng khác",
        "completed_steps": []
    }

    async for event in app.astream(initial_input):
        for node_name, output_state in event.items():
            print(f"🔄 [NODE EXECUTED]: {node_name}")
            if "next_step" in output_state:
                print(f"🎯 Supervisor chỉ định bước tiếp theo: -> {output_state['next_step']}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(run_supervisor_test())