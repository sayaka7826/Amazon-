"""
Amazon広告分析ツール - 設定ファイル
"""
import os
from dotenv import load_dotenv

# .envファイルから環境変数をロード
load_dotenv()

# ====================
# Amazon Ads API 設定
# ====================
AMAZON_CLIENT_ID = os.getenv("AMAZON_CLIENT_ID", "")
AMAZON_CLIENT_SECRET = os.getenv("AMAZON_CLIENT_SECRET", "")
AMAZON_REFRESH_TOKEN = os.getenv("AMAZON_REFRESH_TOKEN", "")
AMAZON_PROFILE_ID = os.getenv("AMAZON_PROFILE_ID", "")

# API エンドポイント
AMAZON_API_BASE_URL = "https://advertising-api.amazon.com"
AMAZON_API_VERSION = "v2"

# ====================
# 商材・商品設定
# ====================
# 高単価焼酎の基本情報（複数SKU対応）
PRODUCTS = {
    "SKU001": {
        "name": "プレミアム焼酎 黒麹",
        "price": 29000,
        "cost": 12000,
        "profit_per_unit": 17000,
    },
    "SKU002": {
        "name": "プレミアム焼酎 白麹",
        "price": 35000,
        "cost": 14000,
        "profit_per_unit": 21000,
    },
    "SKU003": {
        "name": "プレミアム焼酎 芋焼酎",
        "price": 42000,
        "cost": 17000,
        "profit_per_unit": 25000,
    },
    "SKU004": {
        "name": "プレミアム焼酎 麦焼酎",
        "price": 55000,
        "cost": 22000,
        "profit_per_unit": 33000,
    },
}

# ====================
# 診断機能の適正範囲
# ====================
# ROAS（広告売上高営業利益率）の適正範囲
ROAS_TARGET = {
    "min": 2.0,  # 最小（損益分岐点）
    "ideal": 4.0,  # 理想値
    "max": 8.0,  # 最大（非常に良好）
}

# CPC（クリック単価）の適正範囲 - 高単価商材向けに設定
CPC_TARGET = {
    "min": 50,  # 最小（円）
    "ideal": 200,  # 理想値
    "max": 500,  # 最大（円）
}

# 成約率（Conversion Rate）の適正範囲
CONVERSION_RATE_TARGET = {
    "min": 0.5,  # 最小（%）
    "ideal": 2.0,  # 理想値
    "max": 5.0,  # 最大（%）
}

# ====================
# キーワード判定の閾値
# ====================
# 「昇格候補」判定：オートで月間売上 >= これ
PROMOTION_THRESHOLD = 50000  # 円

# 「除外候補」判定：月間クリック >= これ かつ 売上 <= これ
EXCLUSION_CLICK_THRESHOLD = 100
EXCLUSION_REVENUE_THRESHOLD = 20000  # 円

# ====================
# ダッシュボード設定
# ====================
# ページレイアウト
PAGE_CONFIG = {
    "page_title": "Amazon広告運用ツール",
    "page_icon": "📊",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# チャート色設定
CHART_COLORS = {
    "good": "#28A745",
    "warning": "#FFC107",
    "danger": "#DC3545",
    "info": "#17A2B8",
}

# ====================
# デモモード設定
# ====================
DEMO_MODE = True  # 初期はデモモード有効（本APIなし時）
