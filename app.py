import os
from langchain_core.messages import AIMessage, HumanMessage
import streamlit as st

from src.agent.graph import extract_clean_text, graph_app

# Cấu hình Màn hình
st.set_page_config(
    page_title="Banking Copilot - NBO Assistant",
    page_icon="🏦",
    layout="wide",
)

st.title("🏦 AI Banking Copilot - Quản lý Quan hệ Khách hàng (RM)")

# 1. Sidebar Cấu hình Khách hàng
with st.sidebar:
    st.header("⚙️ Cấu hình Session RM")
    cif_id = st.text_input("Mã CIF Khách hàng:", value="CIF001")
    st.session_state["cif_id"] = cif_id

    st.markdown("---")
    st.markdown("### 📌 Trạng thái Hệ thống")
    st.success("CSDL: SQLite Online (`banking.db`)")
    st.info("Kiến trúc: Hybrid 3-Layer + LangGraph")

# 2. Quản lý Session State Messages
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        AIMessage(
            content="Chào bạn, tôi là trợ lý AI Banking Copilot. Tôi có thể hỗ trợ gì cho công việc Quản lý Quan hệ Khách hàng (RM) của bạn ngày hôm nay?"
        )
    ]

# 3. Hiển thị Lịch sử Chat
for msg in st.session_state["messages"]:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(extract_clean_text(msg.content))

# 4. Nhập Yêu cầu từ RM & Thực thi Token Streaming
user_prompt = st.chat_input(
    "Nhập câu hỏi hoặc 'Phân tích NBO cho khách hàng này'..."
)

if user_prompt:
    # 1. Hiển thị User Message ngay trên UI
    with st.chat_message("user"):
        st.markdown(user_prompt)

    user_msg_obj = HumanMessage(content=user_prompt)
    st.session_state["messages"].append(user_msg_obj)

    inputs = {
        "messages": [user_msg_obj],
        "customer_id": st.session_state["cif_id"],
    }
    config = {"configurable": {"thread_id": "rm_session_1"}}

    # 2. Hứng Token Streaming real-time bằng stream_mode="messages"
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        for chunk, metadata in graph_app.stream(
            inputs, config=config, stream_mode="messages"
        ):
            # Lọc lấy Chunk từ các AI Node chính
            if metadata.get("langgraph_node") in [
                "copilot_chat",
                "nbo_reasoning_specialist",
            ]:
                if hasattr(chunk, "content") and chunk.content:
                    chunk_text = extract_clean_text(chunk.content)
                    if chunk_text:
                        full_response += chunk_text
                        # Cập nhật chữ nhảy từng token + con trỏ ▌
                        message_placeholder.markdown(full_response + "▌")

        # Hoàn tất hiển thị không còn con trỏ
        message_placeholder.markdown(full_response)

        if full_response:
            st.session_state["messages"].append(
                AIMessage(content=full_response)
            )

    st.rerun()