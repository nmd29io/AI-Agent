import sys
from pathlib import Path

# Thêm root dir vào sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

import asyncio
from dotenv import load_dotenv

# Load biến môi trường với override=True để ghi đè API Key chuẩn
load_dotenv(override=True)

from src.agent.graph import app


async def run_pipeline():
    print("🚀 --- ĐANG KHỞI CHẠY PIPELINE THẨM ĐỊNH TÍN DỤNG --- 🚀\n")

    # 1. Giả lập Input từ RM (Quản lý Quan hệ Khách hàng)
    initial_input = {
        "company_tax_code": "9853801961",  # Công ty Alpha (Dữ liệu tốt)
        "loan_amount_requested": 8_000_000_000.0,
        "loan_purpose": "Bổ sung vốn lưu động mua nguyên vật liệu sản xuất hạt nhựa",
    }

    # 2. Thực thi Graph qua astream (Streaming từng Node)
    async for event in app.astream(initial_input):
        for node_name, output_state in event.items():
            print(f"✔️ [HOÀN THÀNH NODE]: {node_name}")
            
            # In tin nhắn log do Node tạo ra (nếu có)
            if "messages" in output_state and output_state["messages"]:
                last_msg = output_state["messages"][-1].content
                print(f"💬 Log:\n{last_msg}\n")
            print("-" * 60)

    # 3. Lấy kết quả State cuối cùng
    final_state = await app.ainvoke(initial_input)
    assessment = final_state.get("assessment_result", {})

    print("\n=================== TỜ TRÌNH THẨM ĐỊNH TÍN DỤNG ===================")
    print(f"📌 QUYẾT ĐỊNH: {assessment.get('decision')}")
    print(f"💰 HẠN MỨC ĐỀ XUẤT: {assessment.get('recommended_credit_limit', 0):,.0f} VNĐ")
    print(f"⚠️ MỨC ĐỘ RỦI RO: {assessment.get('risk_level')}")
    print("\n📄 CHI TIẾT TỜ TRÌNH MARKDOWN:")
    print(assessment.get("submission_report_markdown"))


if __name__ == "__main__":
    asyncio.run(run_pipeline())