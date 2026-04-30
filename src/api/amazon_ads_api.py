"""
Amazon Ads API 連携モジュール
Amazon Ads APIを通じて、広告パフォーマンスデータを取得
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AmazonAdsAPI:
    """Amazon Ads API のラッパークラス"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        profile_id: str,
        use_mock_data: bool = True,
    ):
        """
        初期化

        Args:
            client_id: Amazon APIのClient ID
            client_secret: Amazon APIのClient Secret
            refresh_token: リフレッシュトークン
            profile_id: プロファイルID
            use_mock_data: Trueの場合、モックデータを返す（テスト用）
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.profile_id = profile_id
        self.use_mock_data = use_mock_data or not (client_id and client_secret)
        self.access_token = None
        self.base_url = "https://advertising-api.amazon.com"

        if not self.use_mock_data:
            self._refresh_access_token()

    def _refresh_access_token(self) -> bool:
        """アクセストークンをリフレッシュ"""
        if not self.client_id or not self.client_secret:
            logger.warning("API credentials not configured. Using mock data mode.")
            self.use_mock_data = True
            return False

        try:
            url = "https://api.amazon.com/auth/o2/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            logger.info("Access token refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            self.use_mock_data = True
            return False

    def _get_headers(self) -> Dict[str, str]:
        """APIリクエストヘッダーを生成"""
        headers = {
            "Content-Type": "application/json",
            "Amazon-Advertising-API-Scope": self.profile_id,
            "User-Agent": "AmazonAdsAnalysisTool/1.0",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def get_campaigns(self) -> List[Dict[str, Any]]:
        """
        キャンペーン一覧を取得

        Returns:
            キャンペーンのリスト
        """
        if self.use_mock_data:
            return self._mock_campaigns()

        try:
            url = f"{self.base_url}/v2/campaigns"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return response.json().get("campaigns", [])
        except Exception as e:
            logger.error(f"Failed to get campaigns: {e}")
            return self._mock_campaigns()

    def get_campaign_performance(
        self, start_date: str, end_date: str, group_by: str = "CAMPAIGN"
    ) -> List[Dict[str, Any]]:
        """
        キャンペーンのパフォーマンスデータを取得

        Args:
            start_date: 開始日 (YYYYMMDD形式)
            end_date: 終了日 (YYYYMMDD形式)
            group_by: グループ化方法 (CAMPAIGN, AD_GROUP, KEYWORD など)

        Returns:
            パフォーマンスデータのリスト
        """
        if self.use_mock_data:
            return self._mock_performance_data(start_date, end_date, group_by)

        try:
            url = f"{self.base_url}/v2/reports"
            params = {
                "startDate": start_date,
                "endDate": end_date,
                "groupBy": group_by,
                "metrics": [
                    "impressions",
                    "clicks",
                    "cost",
                    "conversions",
                    "sales",
                ],
            }
            response = requests.get(
                url, headers=self._get_headers(), params=params, timeout=10
            )
            response.raise_for_status()
            return response.json().get("reports", [])
        except Exception as e:
            logger.error(f"Failed to get campaign performance: {e}")
            return self._mock_performance_data(start_date, end_date, group_by)

    def get_keywords(self, campaign_id: str) -> List[Dict[str, Any]]:
        """
        キャンペーン内のキーワードを取得

        Args:
            campaign_id: キャンペーンID

        Returns:
            キーワードのリスト
        """
        if self.use_mock_data:
            return self._mock_keywords(campaign_id)

        try:
            url = f"{self.base_url}/v2/keywords"
            params = {"campaignId": campaign_id}
            response = requests.get(
                url, headers=self._get_headers(), params=params, timeout=10
            )
            response.raise_for_status()
            return response.json().get("keywords", [])
        except Exception as e:
            logger.error(f"Failed to get keywords: {e}")
            return self._mock_keywords(campaign_id)

    def get_negative_keywords(self, campaign_id: str) -> List[Dict[str, Any]]:
        """除外キーワードを取得"""
        if self.use_mock_data:
            return self._mock_negative_keywords()

        try:
            url = f"{self.base_url}/v2/negative-keywords"
            params = {"campaignId": campaign_id}
            response = requests.get(
                url, headers=self._get_headers(), params=params, timeout=10
            )
            response.raise_for_status()
            return response.json().get("negativeKeywords", [])
        except Exception as e:
            logger.error(f"Failed to get negative keywords: {e}")
            return self._mock_negative_keywords()

    # ==========================================
    # モックデータ生成メソッド
    # ==========================================

    def _mock_campaigns(self) -> List[Dict[str, Any]]:
        """モックキャンペーンデータ"""
        return [
            {
                "campaignId": "1001",
                "name": "オート広告 - 全体",
                "type": "AUTO",
                "state": "ENABLED",
                "dailyBudget": 50000,
            },
            {
                "campaignId": "1002",
                "name": "マニュアル広告 - ブランド指名",
                "type": "MANUAL",
                "state": "ENABLED",
                "dailyBudget": 30000,
            },
            {
                "campaignId": "1003",
                "name": "マニュアル広告 - 競合品指名",
                "type": "MANUAL",
                "state": "ENABLED",
                "dailyBudget": 20000,
            },
        ]

    def _mock_performance_data(
        self, start_date: str, end_date: str, group_by: str
    ) -> List[Dict[str, Any]]:
        """モックパフォーマンスデータ"""
        return [
            {
                "campaignId": "1001",
                "campaignName": "オート広告 - 全体",
                "impressions": 5000,
                "clicks": 250,
                "cost": 45000,  # 250 * 180 JPY/click
                "conversions": 8,
                "sales": 200000,  # 8 * 25000 JPY/unit average
                "roas": 200000 / 45000,  # 4.44
            },
            {
                "campaignId": "1002",
                "campaignName": "マニュアル広告 - ブランド指名",
                "impressions": 3000,
                "clicks": 200,
                "cost": 35000,  # 200 * 175 JPY/click
                "conversions": 6,
                "sales": 150000,  # 6 * 25000 JPY/unit average
                "roas": 150000 / 35000,  # 4.29
            },
            {
                "campaignId": "1003",
                "campaignName": "マニュアル広告 - 競合品指名",
                "impressions": 2000,
                "clicks": 80,
                "cost": 16000,  # 80 * 200 JPY/click
                "conversions": 2,
                "sales": 60000,  # 2 * 30000 JPY/unit average
                "roas": 60000 / 16000,  # 3.75
            },
        ]

    def _mock_keywords(self, campaign_id: str) -> List[Dict[str, Any]]:
        """モックキーワードデータ"""
        keywords = {
            "1001": [  # オート広告
                {
                    "keywordId": "K001",
                    "keyword": "焼酎 プレミアム",
                    "matchType": "auto",
                    "impressions": 2000,
                    "clicks": 120,
                    "cost": 21600,
                    "conversions": 5,
                    "sales": 125000,
                },
                {
                    "keywordId": "K002",
                    "keyword": "高級 焼酎",
                    "matchType": "auto",
                    "impressions": 1500,
                    "clicks": 80,
                    "cost": 14400,
                    "conversions": 2,
                    "sales": 50000,
                },
                {
                    "keywordId": "K003",
                    "keyword": "焼酎 ギフト",
                    "matchType": "auto",
                    "impressions": 1000,
                    "clicks": 30,
                    "cost": 5400,
                    "conversions": 1,
                    "sales": 25000,
                },
                {
                    "keywordId": "K004",
                    "keyword": "焼酎",
                    "matchType": "auto",
                    "impressions": 500,
                    "clicks": 20,
                    "cost": 3600,
                    "conversions": 0,
                    "sales": 0,
                },
            ],
            "1002": [  # マニュアル - ブランド指名
                {
                    "keywordId": "K101",
                    "keyword": "プレミアム焼酎 黒麹",
                    "matchType": "exact",
                    "impressions": 1500,
                    "clicks": 150,
                    "cost": 26250,
                    "conversions": 4,
                    "sales": 100000,
                },
                {
                    "keywordId": "K102",
                    "keyword": "黒麹焼酎",
                    "matchType": "phrase",
                    "impressions": 1000,
                    "clicks": 40,
                    "cost": 7000,
                    "conversions": 1,
                    "sales": 25000,
                },
            ],
            "1003": [  # マニュアル - 競合品指名
                {
                    "keywordId": "K201",
                    "keyword": "競合品A 焼酎",
                    "matchType": "exact",
                    "impressions": 1200,
                    "clicks": 50,
                    "cost": 10000,
                    "conversions": 2,
                    "sales": 50000,
                },
                {
                    "keywordId": "K202",
                    "keyword": "競合品B",
                    "matchType": "phrase",
                    "impressions": 800,
                    "clicks": 30,
                    "cost": 6000,
                    "conversions": 0,
                    "sales": 0,
                },
            ],
        }
        return keywords.get(campaign_id, [])

    def _mock_negative_keywords(self) -> List[Dict[str, Any]]:
        """モック除外キーワード"""
        return [
            {"negativeKeywordId": "N001", "keyword": "焼酎 激安"},
            {"negativeKeywordId": "N002", "keyword": "焼酎 中古"},
            {"negativeKeywordId": "N003", "keyword": "焼酎 格安"},
        ]
