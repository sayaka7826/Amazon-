"""
データハンドリング - CSVやJSONからデータを読み込み
"""
import pandas as pd
import json
from typing import Dict, List, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataHandler:
    """CSVやJSONからデータを読み込むクラス"""

    COLUMN_ALIASES = {
        "campaignId": [
            "campaignId",
            "キャンペーンID",
            "キャンペーン ID",
            "Campaign ID",
            "キャンペーンのID",
        ],
        "campaignName": [
            "campaignName",
            "キャンペーン名",
            "Campaign Name",
            "キャンペーンの名前",
        ],
        "impressions": [
            "impressions",
            "インプレッション",
            "Impressions",
        ],
        "clicks": [
            "clicks",
            "クリック数",
            "Clicks",
        ],
        "cost": [
            "cost",
            "合計費用",
            "Total Cost",
            "広告費",
            "合計コスト",
        ],
        "conversions": [
            "conversions",
            "商品購入数",
            "購入数",
            "Conversions",
            "コンバージョン数",
            "商品購入数（プロモーション）",
        ],
        "sales": [
            "sales",
            "売上",
            "Sales",
            "長期売上",
        ],
        "keyword": [
            "keyword",
            "キーワード",
            "検索語句",
            "Keyword",
            "ターゲット値",
        ],
        "matchType": [
            "matchType",
            "マッチタイプ",
            "Match Type",
            "ターゲットマッチタイプ",
        ],
    }

    @staticmethod
    def load_delimited_file(file_data) -> "pd.DataFrame":
        """スペース区切りやCSVを自動判定して読み込む"""
        try:
            df = pd.read_csv(
                file_data,
                sep=None,
                engine="python",
                encoding="utf-8",
                skipinitialspace=True,
            )
            return df
        except Exception:
            file_data.seek(0)
            df = pd.read_csv(
                file_data,
                delim_whitespace=True,
                encoding="utf-8",
            )
            return df

    @classmethod
    def normalize_headers(cls, df: "pd.DataFrame") -> "pd.DataFrame":
        """日本語ヘッダーや別名ヘッダーを標準カラム名に変換"""
        mapping = {}
        lower_cols = {col.lower().strip(): col for col in df.columns}

        for target, aliases in cls.COLUMN_ALIASES.items():
            for alias in aliases:
                alias_key = alias.lower().strip()
                if alias_key in lower_cols:
                    mapping[lower_cols[alias_key]] = target
                    break

        return df.rename(columns=mapping)

    @staticmethod
    def aggregate_campaign_rows(df: "pd.DataFrame") -> "pd.DataFrame":
        """同じキャンペーンIDが複数行ある場合に集計する"""
        if df["campaignId"].duplicated().any():
            numeric_cols = ["impressions", "clicks", "cost", "conversions", "sales"]
            agg = {col: "sum" for col in numeric_cols if col in df.columns}
            agg["campaignName"] = "first"
            df = df.groupby("campaignId", as_index=False).agg(agg)
        return df

    @classmethod
    def read_csv_campaigns(cls, csv_data) -> List[Dict[str, Any]]:
        """
        キャンペーンデータをCSVまたはスペース区切りで読み込み
        """
        try:
            df = cls.load_delimited_file(csv_data)
            df = cls.normalize_headers(df)

            required_cols = [
                "campaignId",
                "campaignName",
                "impressions",
                "clicks",
                "cost",
                "conversions",
                "sales",
            ]

            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(
                    "必須カラムが不足しています: "
                    + ", ".join(missing_cols)
                    + "\n検出されたカラム: "
                    + ", ".join(df.columns.astype(str))
                )

            df["cost"] = pd.to_numeric(df["cost"], errors="coerce")
            df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce").fillna(0).astype(int)
            df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").fillna(0).astype(int)
            df["conversions"] = pd.to_numeric(df["conversions"], errors="coerce").fillna(0).astype(int)
            df["sales"] = pd.to_numeric(df["sales"], errors="coerce")

            df = cls.aggregate_campaign_rows(df)
            campaigns = df.to_dict("records")
            logger.info(f"Loaded {len(campaigns)} campaigns from uploaded data")
            return campaigns

        except Exception as e:
            logger.error(f"Error reading campaigns file: {e}")
            raise

    @classmethod
    def read_csv_keywords(cls, csv_data) -> List[Dict[str, Any]]:
        """
        キーワードデータをCSVまたはスペース区切りで読み込み
        """
        try:
            df = cls.load_delimited_file(csv_data)
            df = cls.normalize_headers(df)

            required_cols = [
                "campaignId",
                "keyword",
                "impressions",
                "clicks",
                "cost",
                "conversions",
                "sales",
            ]

            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(
                    "必須カラムが不足しています: "
                    + ", ".join(missing_cols)
                    + "\n検出されたカラム: "
                    + ", ".join(df.columns.astype(str))
                )

            df["cost"] = pd.to_numeric(df["cost"], errors="coerce")
            df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce").fillna(0).astype(int)
            df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").fillna(0).astype(int)
            df["conversions"] = pd.to_numeric(df["conversions"], errors="coerce").fillna(0).astype(int)
            df["sales"] = pd.to_numeric(df["sales"], errors="coerce")

            if "matchType" not in df.columns:
                df["matchType"] = "unknown"

            keywords = df.to_dict("records")
            logger.info(f"Loaded {len(keywords)} keywords from uploaded data")
            return keywords

        except Exception as e:
            logger.error(f"Error reading keywords file: {e}")
            raise

    @staticmethod
    def validate_campaign_data(campaigns: List[Dict[str, Any]]) -> bool:
        """キャンペーンデータの妥当性を検証"""
        if not campaigns:
            return False

        for campaign in campaigns:
            # 必須フィールド
            if "campaignId" not in campaign or "campaignName" not in campaign:
                logger.warning(f"Missing required fields in campaign: {campaign}")
                return False

            # 数値フィールドの確認
            numeric_fields = ["impressions", "clicks", "cost", "conversions", "sales"]
            for field in numeric_fields:
                if field in campaign:
                    if not isinstance(campaign[field], (int, float)):
                        try:
                            campaign[field] = float(campaign[field])
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid value for {field}: {campaign[field]}")
                            return False

        return True

    @staticmethod
    def validate_keyword_data(keywords: List[Dict[str, Any]]) -> bool:
        """キーワードデータの妥当性を検証"""
        if not keywords:
            return False

        for keyword in keywords:
            # 必須フィールド
            if "campaignId" not in keyword or "keyword" not in keyword:
                logger.warning(f"Missing required fields in keyword: {keyword}")
                return False

            # 数値フィールドの確認
            numeric_fields = ["impressions", "clicks", "cost", "conversions", "sales"]
            for field in numeric_fields:
                if field in keyword:
                    if not isinstance(keyword[field], (int, float)):
                        try:
                            keyword[field] = float(keyword[field])
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid value for {field}: {keyword[field]}")
                            return False

        return True

    @staticmethod
    def export_template_campaigns_csv() -> str:
        """キャンペーンCSVテンプレートを生成"""
        template_data = {
            "campaignId": ["1001", "1002", "1003"],
            "campaignName": [
                "オート広告 - 全体",
                "マニュアル広告 - ブランド指名",
                "マニュアル広告 - 競合品指名",
            ],
            "type": ["AUTO", "MANUAL", "MANUAL"],
            "impressions": [5000, 3000, 2000],
            "clicks": [250, 200, 80],
            "cost": [45000, 35000, 16000],
            "conversions": [8, 6, 2],
            "sales": [200000, 150000, 60000],
        }
        df = pd.DataFrame(template_data)
        return df.to_csv(index=False)

    @staticmethod
    def export_template_keywords_csv() -> str:
        """キーワードCSVテンプレートを生成"""
        template_data = {
            "campaignId": ["1001", "1001", "1001"],
            "keyword": ["焼酎 プレミアム", "高級 焼酎", "焼酎 ギフト"],
            "matchType": ["auto", "auto", "auto"],
            "impressions": [2000, 1500, 1000],
            "clicks": [120, 80, 30],
            "cost": [21600, 14400, 5400],
            "conversions": [5, 2, 1],
            "sales": [125000, 50000, 25000],
        }
        df = pd.DataFrame(template_data)
        return df.to_csv(index=False)

    @staticmethod
    def campaigns_to_json(campaigns: List[Dict[str, Any]]) -> str:
        """キャンペーンデータをJSON形式に変換"""
        return json.dumps(campaigns, ensure_ascii=False, indent=2)

    @staticmethod
    def keywords_to_json(keywords: List[Dict[str, Any]]) -> str:
        """キーワードデータをJSON形式に変換"""
        return json.dumps(keywords, ensure_ascii=False, indent=2)
