"""
キーワード昇格・除外アドバイザー
オートで売れたキーワードをマニュアルに昇格、
売れないのにクリックが多いキーワードを除外
"""
from typing import Dict, List, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KeywordAdvisor:
    """キーワード提案・除外判定クラス"""

    def __init__(self, config: Dict[str, Any]):
        """
        初期化

        Args:
            config: 設定辞書
        """
        self.config = config
        self.promotion_threshold = config.get("PROMOTION_THRESHOLD", 50000)
        self.exclusion_click_threshold = config.get("EXCLUSION_CLICK_THRESHOLD", 100)
        self.exclusion_revenue_threshold = config.get(
            "EXCLUSION_REVENUE_THRESHOLD", 20000
        )

    def classify_keywords(
        self, keywords: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        キーワードを分類（昇格候補、除外候補、要監視）

        Args:
            keywords: キーワードリスト
                各要素: {
                    'keyword': str,
                    'impressions': int,
                    'clicks': int,
                    'cost': float,
                    'conversions': int,
                    'sales': float,
                }

        Returns:
            {
                'promotion': [...],  # 昇格候補
                'exclusion': [...],  # 除外候補
                'monitoring': [...], # 要監視
            }
        """
        promotion = []
        exclusion = []
        monitoring = []

        for keyword in keywords:
            classification = self.classify_single_keyword(keyword)
            keyword_with_class = {**keyword, "classification": classification}

            if classification == "promotion":
                promotion.append(keyword_with_class)
            elif classification == "exclusion":
                exclusion.append(keyword_with_class)
            else:
                monitoring.append(keyword_with_class)

        return {
            "promotion": sorted(promotion, key=lambda x: x["sales"], reverse=True),
            "exclusion": sorted(exclusion, key=lambda x: x["clicks"], reverse=True),
            "monitoring": sorted(
                monitoring, key=lambda x: x["conversions"], reverse=True
            ),
        }

    def classify_single_keyword(self, keyword: Dict[str, Any]) -> str:
        """
        単一キーワードの分類

        Args:
            keyword: キーワードデータ

        Returns:
            "promotion" | "exclusion" | "monitoring"
        """
        sales = keyword.get("sales", 0)
        clicks = keyword.get("clicks", 0)
        conversions = keyword.get("conversions", 0)

        # 昇格候補: 月間売上がしきい値以上
        if sales >= self.promotion_threshold:
            return "promotion"

        # 除外候補: クリックが多いのに売上がない、または少ない
        if (
            clicks >= self.exclusion_click_threshold
            and sales < self.exclusion_revenue_threshold
        ):
            return "exclusion"

        # 要監視
        return "monitoring"

    def generate_promotion_advice(
        self, keyword: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        昇格キーワードに対する具体的なアドバイスを生成

        Args:
            keyword: キーワードデータ

        Returns:
            {
                'keyword': str,
                'current_performance': {...},
                'recommended_actions': [...],
                'estimated_impact': {...},
            }
        """
        sales = keyword.get("sales", 0)
        clicks = keyword.get("clicks", 0)
        cost = keyword.get("cost", 0)
        conversions = keyword.get("conversions", 0)

        # 成約率とコスト効率を計算
        conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
        roas = (sales / cost) if cost > 0 else 0

        recommendations = [
            f"✅ このキーワードは月間売上 {sales:,.0f}円 と優秀です。",
            f"🎯 成約率 {conversion_rate:.2f}% で、ROASは {roas:.2f} です。",
            f"📌 マニュアル広告に昇格してください。",
            f"💡 推奨入札額: 現在のCPC（{cost/clicks if clicks > 0 else 0:.0f}円）×1.2～1.5倍を検討してください。",
            f"📊 昇格後は、より高い入札額で上位表示を狙い、さらなる売上増を期待できます。",
        ]

        # 昇格による推定インパクト
        # 位置が改善されると仮定してCTRが20%増加、成約率も5%向上と仮定
        estimated_impact = {
            "estimated_sales_increase_pct": 25,  # 25%増加を想定
            "estimated_additional_revenue": sales * 0.25,
            "estimated_additional_cost": cost * 0.2,  # 20%コスト増加
            "estimated_net_profit_increase": (sales * 0.25) - (cost * 0.2),
        }

        return {
            "keyword": keyword.get("keyword", ""),
            "current_performance": {
                "sales": sales,
                "clicks": clicks,
                "cost": cost,
                "conversions": conversions,
                "conversion_rate": conversion_rate,
                "roas": roas,
            },
            "recommended_actions": recommendations,
            "estimated_impact": estimated_impact,
        }

    def generate_exclusion_advice(
        self, keyword: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        除外キーワードに対する具体的なアドバイスを生成

        Args:
            keyword: キーワードデータ

        Returns:
            {
                'keyword': str,
                'problem_analysis': {...},
                'recommended_actions': [...],
                'expected_savings': {...},
            }
        """
        clicks = keyword.get("clicks", 0)
        cost = keyword.get("cost", 0)
        sales = keyword.get("sales", 0)
        conversions = keyword.get("conversions", 0)

        cpc = cost / clicks if clicks > 0 else 0
        conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0

        recommendations = [
            f"❌ このキーワードは月間 {clicks} クリック で、売上は {sales:,.0f}円 のみです。",
            f"🔴 CPC {cpc:.0f}円 に対して、成約していません（成約率 {conversion_rate:.2f}%）。",
            f"💸 無駄な広告費：{cost:,.0f}円 / 月",
            f"🚫 このキーワードを除外することを強く推奨します。",
            f"📝 複数キャンペーン間で除外キーワードの統一を検討してください。",
        ]

        # 期待される削減効果
        expected_savings = {
            "cost_waste_monthly": cost,
            "cost_waste_annual": cost * 12,
            "estimated_roas_improvement_pct": (cost / (cost + sales) * 100)
            if (cost + sales) > 0
            else 0,
        }

        return {
            "keyword": keyword.get("keyword", ""),
            "problem_analysis": {
                "clicks": clicks,
                "cost": cost,
                "sales": sales,
                "conversions": conversions,
                "cpc": cpc,
                "conversion_rate": conversion_rate,
            },
            "recommended_actions": recommendations,
            "expected_savings": expected_savings,
        }

    def analyze_keyword_portfolio(
        self, keywords: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        キーワードポートフォリオ全体を分析

        Args:
            keywords: キーワードリスト

        Returns:
            {
                'total_analysis': {...},
                'recommendations': [...],
                'opportunities': {...},
            }
        """
        if not keywords:
            return {
                "total_analysis": {},
                "recommendations": ["データがありません"],
                "opportunities": {},
            }

        classified = self.classify_keywords(keywords)

        total_sales = sum(k.get("sales", 0) for k in keywords)
        total_cost = sum(k.get("cost", 0) for k in keywords)
        total_clicks = sum(k.get("clicks", 0) for k in keywords)
        total_conversions = sum(k.get("conversions", 0) for k in keywords)

        promotion_sales = sum(k.get("sales", 0) for k in classified["promotion"])
        exclusion_cost = sum(k.get("cost", 0) for k in classified["exclusion"])

        recommendations = []

        if classified["promotion"]:
            recommendations.append(
                f"🎯 {len(classified['promotion'])}個の昇格候補キーワードがあります。"
                f"これらの合計売上は {promotion_sales:,.0f}円 です。"
            )

        if classified["exclusion"]:
            recommendations.append(
                f"🚫 {len(classified['exclusion'])}個の除外候補があります。"
                f"これらの無駄な広告費は月 {exclusion_cost:,.0f}円 です。"
            )

        opportunities = {
            "promotion_candidates": len(classified["promotion"]),
            "promotion_sales": promotion_sales,
            "exclusion_candidates": len(classified["exclusion"]),
            "exclusion_cost_waste": exclusion_cost,
            "monitoring_count": len(classified["monitoring"]),
        }

        return {
            "classified_keywords": classified,
            "total_analysis": {
                "total_keywords": len(keywords),
                "total_sales": total_sales,
                "total_cost": total_cost,
                "total_clicks": total_clicks,
                "total_conversions": total_conversions,
                "overall_roas": (total_sales / total_cost) if total_cost > 0 else 0,
            },
            "recommendations": recommendations,
            "opportunities": opportunities,
        }
