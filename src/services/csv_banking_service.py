import os
from typing import Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

# 1. Pydantic Schema để Validate Dữ liệu đọc từ CSV


class CorporateCreditReportSchema(BaseModel):
    company_tax_code: str
    company_name: str
    establishment_year: int
    debt_group: str
    credit_score: int
    overdue_36m_count: int
    total_current_debt: float
    internal_rating: str

# 2. Service truy vấn CSDL CSV


class CSVBankingService:
    def __init__(self, csv_file_path: str = "data/cic_crm_database.csv"):
        self.csv_file_path = csv_file_path
        self._load_data()

    def _load_data(self):
        """Đọc và cache file CSV vào bộ nhớ RAM"""
        if not os.path.exists(self.csv_file_path):
            raise FileNotFoundError(f"Không tìm thấy file CSDL CSV tại: {self.csv_file_path}")

        # Đọc MST dưới dạng string để không bị mất số 0 ở đầu
        self.df = pd.read_csv(self.csv_file_path, dtype={"company_tax_code": str})

    async def fetch_credit_report(self, tax_code: str) -> CorporateCreditReportSchema:
        """Truy vấn bản ghi doanh nghiệp theo Mã số thuế (MST)"""
        # Lọc bản ghi theo tax_code
        matched = self.df[self.df["company_tax_code"] == tax_code]

        if matched.empty:
            # Dữ liệu fallback mặc định nếu không tìm thấy MST trong CSV
            return CorporateCreditReportSchema(
                company_tax_code=tax_code,
                company_name="Doanh nghiệp Chưa có trên Hệ thống CRM",
                establishment_year=2024,
                debt_group="Nhóm 1 - Nợ chuẩn",
                credit_score=600,
                overdue_36m_count=0,
                total_current_debt=0.0,
                internal_rating="B"
            )

        # Chuyển dòng dữ liệu đầu tiên thành Dictionary
        record = matched.iloc[0].to_dict()
        return CorporateCreditReportSchema(**record)
