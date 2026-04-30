"""
自動データ取得スクリプト - Amazon Ads APIから毎日データをダウンロード
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import csv
import logging
from typing import List, Dict, Any

# パスを設定
sys.path.insert(0, str(Path(__file__).parent))

from config.config import (
    AMAZON_CLIENT_ID,
    AMAZON_CLIENT_SECRET,
    AMAZON_REFRESH_TOKEN,
    AMAZON_PROFILE_ID,
)
from src.api import AmazonAdsAPI

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AutoDataUpdater:
    """自動データ更新クラス"""

    def __init__(self):
        """初期化"""
        self.api = AmazonAdsAPI(
            client_id=AMAZON_CLIENT_ID,
            client_secret=AMAZON_CLIENT_SECRET,
            refresh_token=AMAZON_REFRESH_TOKEN,
            profile_id=AMAZON_PROFILE_ID,
            use_mock_data=False,
        )
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)

    def get_yesterday_date_range(self) -> tuple[str, str]:
        """昨日の日付範囲を取得"""
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")
        return date_str, date_str

    def fetch_campaign_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """キャンペーンデータを取得"""
        logger.info(f"Fetching campaign data from {start_date} to {end_date}")
        campaigns = self.api.get_campaigns()
        campaign_performance = self.api.get_campaign_performance(start_date, end_date)

        if not campaign_performance:
            logger.warning("No campaign data retrieved")
            return []

        logger.info(f"Retrieved {len(campaign_performance)} campaigns")
        return campaign_performance

    def fetch_keyword_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """キーワードデータを取得"""
        logger.info(f"Fetching keyword data from {start_date} to {end_date}")

        campaigns = self.api.get_campaigns()
        all_keywords = []

        for campaign in campaigns:
            campaign_id = campaign.get("campaignId")
            logger.info(f"Fetching keywords for campaign {campaign_id}")

            keywords = self.api.get_keywords(campaign_id)
            for keyword in keywords:
                keyword["campaignId"] = campaign_id
                all_keywords.append(keyword)

        logger.info(f"Retrieved {len(all_keywords)} keywords")
        return all_keywords

    def save_as_csv(self, data: List[Dict[str, Any]], filename: str) -> Path:
        """データをCSVで保存"""
        if not data:
            logger.warning(f"No data to save for {filename}")
            return None

        filepath = self.data_dir / filename

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

            logger.info(f"Saved {len(data)} records to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
            return None

    def save_as_json(self, data: List[Dict[str, Any]], filename: str) -> Path:
        """データをJSONで保存"""
        if not data:
            logger.warning(f"No data to save for {filename}")
            return None

        filepath = self.data_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved {len(data)} records to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving JSON: {e}")
            return None

    def update_daily(self, include_csv: bool = True, include_json: bool = True):
        """毎日のデータ更新を実行"""
        logger.info("=" * 60)
        logger.info("Starting daily data update")
        logger.info("=" * 60)

        # 日付範囲を取得
        start_date, end_date = self.get_yesterday_date_range()
        logger.info(f"Date range: {start_date} to {end_date}")

        # キャンペーンデータを取得
        campaigns_data = self.fetch_campaign_data(start_date, end_date)

        if campaigns_data:
            # タイムスタンプ付きファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if include_csv:
                self.save_as_csv(
                    campaigns_data,
                    f"campaigns_{timestamp}.csv"
                )

            if include_json:
                self.save_as_json(
                    campaigns_data,
                    f"campaigns_{timestamp}.json"
                )

            # 最新ファイルも保存（常に上書き）
            self.save_as_csv(campaigns_data, "campaigns_latest.csv")
            self.save_as_json(campaigns_data, "campaigns_latest.json")

        # キーワードデータを取得
        keywords_data = self.fetch_keyword_data(start_date, end_date)

        if keywords_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if include_csv:
                self.save_as_csv(
                    keywords_data,
                    f"keywords_{timestamp}.csv"
                )

            if include_json:
                self.save_as_json(
                    keywords_data,
                    f"keywords_{timestamp}.json"
                )

            # 最新ファイルも保存（常に上書き）
            self.save_as_csv(keywords_data, "keywords_latest.csv")
            self.save_as_json(keywords_data, "keywords_latest.json")

        logger.info("=" * 60)
        logger.info("Daily data update completed successfully")
        logger.info("=" * 60)


def main():
    """メイン関数"""
    try:
        updater = AutoDataUpdater()
        updater.update_daily(include_csv=True, include_json=True)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
