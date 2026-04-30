"""
Google Sheets 永続ストレージ
アップロードしたキャンペーン・キーワードデータをシートに保存・読み込み
"""
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

NUMERIC_COLS = ["impressions", "clicks", "cost", "conversions", "sales"]


class SheetsHandler:
    CAMPAIGNS_SHEET = "campaigns"
    KEYWORDS_SHEET = "keywords"

    def __init__(self, spreadsheet_id: str, credentials_info: dict):
        creds = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        self.spreadsheet = client.open_by_key(spreadsheet_id)
        self._ensure_sheets()

    PRODUCTS_SHEET = "products"

    def _ensure_sheets(self):
        existing = {ws.title for ws in self.spreadsheet.worksheets()}
        if self.CAMPAIGNS_SHEET not in existing:
            self.spreadsheet.add_worksheet(self.CAMPAIGNS_SHEET, 1000, 20)
        if self.KEYWORDS_SHEET not in existing:
            self.spreadsheet.add_worksheet(self.KEYWORDS_SHEET, 5000, 20)
        if self.PRODUCTS_SHEET not in existing:
            self.spreadsheet.add_worksheet(self.PRODUCTS_SHEET, 100, 10)

    def _to_numeric(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for r in records:
            for key in NUMERIC_COLS:
                if key in r and r[key] != "":
                    try:
                        r[key] = float(r[key])
                    except (ValueError, TypeError):
                        pass
        return records

    def save_campaigns(self, campaigns: List[Dict[str, Any]]) -> None:
        ws = self.spreadsheet.worksheet(self.CAMPAIGNS_SHEET)
        ws.clear()
        if campaigns:
            df = pd.DataFrame(campaigns)
            ws.update([df.columns.tolist()] + df.fillna("").values.tolist())
        logger.info(f"Saved {len(campaigns)} campaigns to Google Sheets")

    def load_campaigns(self) -> List[Dict[str, Any]]:
        ws = self.spreadsheet.worksheet(self.CAMPAIGNS_SHEET)
        records = ws.get_all_records()
        return self._to_numeric(records)

    def save_keywords(self, keywords: List[Dict[str, Any]]) -> None:
        ws = self.spreadsheet.worksheet(self.KEYWORDS_SHEET)
        ws.clear()
        if keywords:
            df = pd.DataFrame(keywords)
            ws.update([df.columns.tolist()] + df.fillna("").values.tolist())
        logger.info(f"Saved {len(keywords)} keywords to Google Sheets")

    def load_keywords(self) -> List[Dict[str, Any]]:
        ws = self.spreadsheet.worksheet(self.KEYWORDS_SHEET)
        records = ws.get_all_records()
        return self._to_numeric(records)

    def save_products(self, products: List[Dict[str, Any]]) -> None:
        ws = self.spreadsheet.worksheet(self.PRODUCTS_SHEET)
        ws.clear()
        if products:
            df = pd.DataFrame(products)
            ws.update([df.columns.tolist()] + df.fillna("").values.tolist())

    def load_products(self) -> List[Dict[str, Any]]:
        ws = self.spreadsheet.worksheet(self.PRODUCTS_SHEET)
        records = ws.get_all_records()
        for r in records:
            for key in ["price", "cost", "profit_per_unit"]:
                if key in r and r[key] != "":
                    try:
                        r[key] = float(r[key])
                    except (ValueError, TypeError):
                        pass
        return records
