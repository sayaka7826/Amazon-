"""
診断機能: 現在の広告設定が適正範囲内かをスコアリング
"""
from typing import Dict, List, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiagnosticsAnalyzer:
    """広告パフォーマンス診断クラス"""

    def __init__(self, config: Dict[str, Any]):
        """
        初期化

        Args:
            config: 設定辞書（適正値の范囲などを含む）
        """
        self.config = config
        self.roas_target = config.get("ROAS_TARGET", {})
        self.cpc_target = config.get("CPC_TARGET", {})
        self.conversion_rate_target = config.get("CONVERSION_RATE_TARGET", {})

    def calculate_roas(self, sales: float, cost: float) -> float:
        """
        ROAS（広告売上高営業利益率）を計算

        Args:
            sales: 売上（円）
            cost: 広告費（円）

        Returns:
            ROAS値（売上÷広告費）
        """
        if cost == 0:
            return 0
        return round(sales / cost, 2)

    def calculate_cpc(self, cost: float, clicks: float) -> float:
        """
        CPC（クリック単価）を計算

        Args:
            cost: 広告費（円）
            clicks: クリック数

        Returns:
            CPC値（円/クリック）
        """
        if clicks == 0:
            return 0
        return round(cost / clicks, 0)

    def calculate_conversion_rate(self, conversions: int, clicks: int) -> float:
        """
        成約率を計算

        Args:
            conversions: 成約数
            clicks: クリック数

        Returns:
            成約率（%）
        """
        if clicks == 0:
            return 0
        return round((conversions / clicks) * 100, 2)

    def score_metric(
        self, value: float, min_val: float, ideal_val: float, max_val: float
    ) -> Tuple[int, str]:
        """
        メトリクスをスコアリング（0-100点）

        Args:
            value: 実績値
            min_val: 最小許容値
            ideal_val: 理想値
            max_val: 最大許容値

        Returns:
            (スコア, 評価)のタプル
        """
        if value < min_val:
            # 最小値以下 → 0-30点
            return (max(0, int(30 * (value / min_val))), "要改善")
        elif value < ideal_val:
            # 最小値～理想値 → 30-70点
            ratio = (value - min_val) / (ideal_val - min_val)
            return (int(30 + 40 * ratio), "改善中")
        elif value < max_val:
            # 理想値～最大値 → 70-90点
            ratio = (value - ideal_val) / (max_val - ideal_val)
            return (int(70 + 20 * ratio), "良好")
        else:
            # 最大値以上 → 90-100点
            return (min(100, int(90 + 10 * (value / max_val))), "優秀")

    def diagnose_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        キャンペーンを診断し、スコアと改善提案を生成

        Args:
            campaign_data: キャンペーンデータ
                {
                    'campaignName': str,
                    'impressions': int,
                    'clicks': int,
                    'cost': float,
                    'conversions': int,
                    'sales': float,
                }

        Returns:
            診断結果
                {
                    'campaign_name': str,
                    'metrics': {...},
                    'scores': {...},
                    'overall_score': int,
                    'recommendations': [str, ...],
                }
        """
        # メトリクス計算
        roas = self.calculate_roas(campaign_data["sales"], campaign_data["cost"])
        cpc = self.calculate_cpc(campaign_data["cost"], campaign_data["clicks"])
        conversion_rate = self.calculate_conversion_rate(
            campaign_data["conversions"], campaign_data["clicks"]
        )

        # スコアリング
        roas_score, roas_eval = self.score_metric(
            roas,
            self.roas_target["min"],
            self.roas_target["ideal"],
            self.roas_target["max"],
        )
        cpc_score, cpc_eval = self.score_metric(
            cpc,
            self.cpc_target["max"],  # CPCは小さいほど良いため逆順
            self.cpc_target["ideal"],
            self.cpc_target["min"],
        )
        cr_score, cr_eval = self.score_metric(
            conversion_rate,
            self.conversion_rate_target["min"],
            self.conversion_rate_target["ideal"],
            self.conversion_rate_target["max"],
        )

        overall_score = (roas_score + cpc_score + cr_score) // 3

        # 改善提案を生成
        recommendations = self._generate_recommendations(
            roas, cpc, conversion_rate, campaign_data
        )

        return {
            "campaign_name": campaign_data.get("campaignName", "Unknown"),
            "metrics": {
                "roas": roas,
                "cpc": cpc,
                "conversion_rate": conversion_rate,
                "impressions": campaign_data.get("impressions", 0),
                "clicks": campaign_data.get("clicks", 0),
                "cost": campaign_data.get("cost", 0),
                "conversions": campaign_data.get("conversions", 0),
                "sales": campaign_data.get("sales", 0),
            },
            "scores": {
                "roas": {"score": roas_score, "evaluation": roas_eval},
                "cpc": {"score": cpc_score, "evaluation": cpc_eval},
                "conversion_rate": {"score": cr_score, "evaluation": cr_eval},
            },
            "overall_score": overall_score,
            "recommendations": recommendations,
        }

    def _generate_recommendations(
        self, roas: float, cpc: float, conversion_rate: float, data: Dict
    ) -> List[str]:
        """改善提案を生成"""
        recommendations = []

        # ROAS分析
        if roas < self.roas_target["min"]:
            recommendations.append(
                f"⚠️ ROAS {roas} は最小値 {self.roas_target['min']} を下回っています。"
                "入札額を下げるか、除外キーワードを見直してください。"
            )
        elif roas < self.roas_target["ideal"]:
            recommendations.append(
                f"📈 ROAS {roas} を理想値 {self.roas_target['ideal']} に向けて改善できます。"
                "高パフォーマンスキーワードの入札額を上げることを検討してください。"
            )

        # CPC分析
        if cpc > self.cpc_target["max"]:
            recommendations.append(
                f"💰 CPC {cpc} 円は上限 {self.cpc_target['max']} 円を超過しています。"
                "入札額を削減するか、品質スコアを改善してください。"
            )

        # 成約率分析
        if conversion_rate < self.conversion_rate_target["min"]:
            recommendations.append(
                f"🔍 成約率 {conversion_rate}% は最小値 {self.conversion_rate_target['min']}% を下回っています。"
                "商品ページやタイトルの改善、または対象外キーワードの除外を検討してください。"
            )

        # トラフィック分析
        if data.get("impressions", 0) < 1000:
            recommendations.append(
                "📊 インプレッション数が少ないです。入札額を上げてボリュームを増やすことを検討してください。"
            )

        if not recommendations:
            recommendations.append(
                "✅ 現在の設定は良好です。引き続き監視してください。"
            )

        return recommendations

    def diagnose_all_campaigns(
        self, campaigns_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        複数キャンペーンを診断

        Args:
            campaigns_data: キャンペーンデータのリスト

        Returns:
            {
                'diagnoses': [診断結果, ...],
                'summary': {...}
            }
        """
        diagnoses = [self.diagnose_campaign(c) for c in campaigns_data]
        avg_score = sum(d["overall_score"] for d in diagnoses) / len(
            diagnoses
        ) if diagnoses else 0

        return {
            "diagnoses": diagnoses,
            "summary": {
                "total_campaigns": len(diagnoses),
                "average_score": round(avg_score, 1),
                "high_performers": [
                    d["campaign_name"] for d in diagnoses if d["overall_score"] >= 70
                ],
                "low_performers": [
                    d["campaign_name"] for d in diagnoses if d["overall_score"] < 50
                ],
            },
        }
