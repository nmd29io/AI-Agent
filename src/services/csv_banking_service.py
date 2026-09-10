import os
import pandas as pd
from pydantic import BaseModel


class CorporateCreditReportSchema(BaseModel):
    company_tax_code: str
    company_name: str
    establishment_year: int
    debt_group: str
    credit_score: int
    overdue_36m_count: int
    total_current_debt: float
    internal_rating: str
    total_liabilities: float = 0.0
    owner_equity: float = 1.0  # Tránh chia cho 0
    ebitda: float = 0.0
    annual_debt_service: float = 1.0  # Tránh chia cho 0


class CSVBankingService:
    def __init__(self, csv_file_path: str = "data/cic_crm_database.csv"):
        self.csv_file_path = csv_file_path
        self._load_data()

    def _load_data(self):
        if not os.path.exists(self.csv_file_path):
            raise FileNotFoundError(f"Không tìm thấy file CSDL CSV tại: {self.csv_file_path}")
        self.df = pd.read_csv(self.csv_file_path, dtype={"company_tax_code": str})

    def _find_matched_row(self, tax_code: str) -> pd.DataFrame:
        code_str = str(tax_code).strip()
        # 1. Khớp chính xác mã số thuế
        matched = self.df[self.df["company_tax_code"].astype(str).str.strip() == code_str]
        # 2. Khớp có bù số 0 đầu (10 chữ số) nếu người dùng gõ thiếu số 0
        if matched.empty and len(code_str) < 10:
            matched = self.df[self.df["company_tax_code"].astype(str).str.strip() == code_str.zfill(10)]
        # 3. Khớp theo tên công ty (không phân biệt hoa thường)
        if matched.empty:
            matched = self.df[self.df["company_name"].astype(str).str.lower().str.strip() == code_str.lower()]
        return matched

    def get_company_by_tax_code(self, tax_code: str):
        """Tra cứu thông tin công ty đồng bộ (phục vụ hiển thị UI)."""
        matched = self._find_matched_row(tax_code)
        if matched.empty:
            return None
        return matched.iloc[0].to_dict()

    async def fetch_credit_report(self, tax_code: str) -> CorporateCreditReportSchema:
        matched = self._find_matched_row(tax_code)
        if matched.empty:
            return CorporateCreditReportSchema(
                company_tax_code=tax_code,
                company_name="Không tìm thấy doanh nghiệp",
                establishment_year=0,
                debt_group="N/A",
                credit_score=0,
                overdue_36m_count=0,
                total_current_debt=0.0,
                internal_rating="N/A",
                total_liabilities=0.0,
                owner_equity=1.0,
                ebitda=0.0,
                annual_debt_service=1.0
            )
        record = matched.iloc[0].to_dict()
        return CorporateCreditReportSchema(**record)
