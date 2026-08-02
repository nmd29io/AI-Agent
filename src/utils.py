from typing import Any, List, Dict
import sqlite3
import pandas as pd


def extract_clean_text(content: Any) -> str:
    """Bóc tách chuỗi văn bản sạch từ content của AIMessage,

    xử lý an toàn cho cả dạng str, list[str], và list[dict] từ Gemini API.
    """
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                if "text" in item and isinstance(item["text"], str):
                    texts.append(item["text"])
                elif "content" in item and isinstance(item["content"], str):
                    texts.append(item["content"])
        return " ".join(texts).strip()

    return str(content).strip()


def query_db(db_path: str, query: str, params: tuple = ()) -> pd.DataFrame:
    """Helper truy vấn SQLite trả về Pandas DataFrame."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df