"""
高単価専用・入札シミュレーター
1本売れた時の利益額から逆算して、1クリックいくらまでなら損しないかを可視化
"""
from typing import Dict, List, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BidSimulator:
    """入札シミュレーター"""

    def __init__(self, products: Dict[str, Dict[str, Any]]):
        """
        初期化

        Args:
            products: 商品情報
                {
                    'SKU001': {
                        'name': str,
                        'price': float,
                        'cost': float,
                        'profit_per_unit': float,
                    },
                    ...
                }
        """
        self.products = products

    def calculate_breakeven_cpc(
        self,
        profit_per_unit: float,
        estimated_conversion_rate: float = 1.0,
        target_roas: float = 2.0,
    ) -> float:
        """
        損益分岐点CPCを計算

        Args:
            profit_per_unit: 1本あたりの利益（円）
            estimated_conversion_rate: 推定成約率（%）
            target_roas: 目標ROAS

        Returns:
            損益分岐点CPC（円/クリック）
        """
        # 損益分岐点 = 利益 ÷ (成約率 × 目標ROAS)
        cr = estimated_conversion_rate / 100
        if cr == 0:
            return 0
        breakeven_cpc = profit_per_unit / (cr * target_roas)
        return round(breakeven_cpc, 0)

    def calculate_roas_at_cpc(
        self,
        cpc: float,
        profit_per_unit: float,
        estimated_conversion_rate: float = 1.0,
    ) -> float:
        """
        特定のCPCでの期待ROASを計算

        Args:
            cpc: クリック単価（円）
            profit_per_unit: 1本あたりの利益（円）
            estimated_conversion_rate: 推定成約率（%）

        Returns:
            期待ROAS
        """
        cr = estimated_conversion_rate / 100
        if cr == 0:
            return 0
        roas = profit_per_unit * cr / cpc
        return round(roas, 2)

    def calculate_monthly_profit_at_cpc(
        self,
        cpc: float,
        monthly_clicks: int,
        profit_per_unit: float,
        estimated_conversion_rate: float = 1.0,
    ) -> Dict[str, float]:
        """
        特定のCPCでの月間利益を計算

        Args:
            cpc: クリック単価（円）
            monthly_clicks: 月間クリック数
            profit_per_unit: 1本あたりの利益（円）
            estimated_conversion_rate: 推定成約率（%）

        Returns:
            {
                'total_cost': float,  # 総広告費
                'conversions': int,   # 推定成約数
                'total_profit_from_sales': float,  # 売上利益
                'net_profit': float,  # 広告費を差引いた純利益
                'roas': float,  # ROAS
            }
        """
        total_cost = cpc * monthly_clicks
        cr = estimated_conversion_rate / 100
        conversions = int(monthly_clicks * cr)
        total_profit_from_sales = conversions * profit_per_unit
        net_profit = total_profit_from_sales - total_cost
        roas = total_profit_from_sales / total_cost if total_cost > 0 else 0

        return {
            "total_cost": round(total_cost, 0),
            "conversions": conversions,
            "total_profit_from_sales": round(total_profit_from_sales, 0),
            "net_profit": round(net_profit, 0),
            "roas": round(roas, 2),
        }

    def calculate_cpc_from_acos(
        self,
        price: float,
        conversion_rate: float,
        target_acos_pct: float,
    ) -> float:
        """ACoS目標からCPCを逆算: CPC = 販売価格 × 成約率 × ACoS%"""
        cr = conversion_rate / 100
        return round(price * cr * (target_acos_pct / 100), 0)

    def simulate_acos_scenarios(
        self,
        price: float,
        monthly_clicks: int,
        profit_per_unit: float,
        conversion_rate: float,
        acos_targets: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """ACoS目標別にCPC・広告費・利益をシミュレーション"""
        if acos_targets is None:
            acos_targets = [5, 7, 10, 12, 15, 18, 20, 25, 30]
        cr = conversion_rate / 100
        conversions = int(monthly_clicks * cr)
        total_sales = price * conversions
        gross_profit = conversions * profit_per_unit

        scenarios = []
        for acos_pct in acos_targets:
            target_cpc = self.calculate_cpc_from_acos(price, conversion_rate, acos_pct)
            ad_spend = target_cpc * monthly_clicks
            net_profit = gross_profit - ad_spend
            roas = total_sales / ad_spend if ad_spend > 0 else 0

            if net_profit >= gross_profit * 0.5:
                performance = "優秀"
            elif net_profit > 0:
                performance = "良好"
            elif net_profit > -gross_profit * 0.2:
                performance = "要改善"
            else:
                performance = "赤字"

            scenarios.append({
                "acos_target": acos_pct,
                "target_cpc": target_cpc,
                "ad_spend": round(ad_spend, 0),
                "conversions": conversions,
                "total_sales": round(total_sales, 0),
                "gross_profit": round(gross_profit, 0),
                "net_profit": round(net_profit, 0),
                "roas": round(roas, 2),
                "performance": performance,
            })
        return scenarios

    def simulate_cpc_scenarios(
        self,
        monthly_clicks: int,
        profit_per_unit: float,
        estimated_conversion_rate: float = 1.0,
        cpc_range: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        複数のCPCシナリオをシミュレーション

        Args:
            monthly_clicks: 月間クリック数
            profit_per_unit: 1本あたりの利益（円）
            estimated_conversion_rate: 推定成約率（%）
            cpc_range: CPCの範囲を指定（Noneの場合は自動生成）

        Returns:
            シナリオリスト
        """
        if cpc_range is None:
            # 利益から逆算した適正CPCの範囲を自動生成
            breakeven_cpc = self.calculate_breakeven_cpc(
                profit_per_unit, estimated_conversion_rate, target_roas=1.0
            )
            ideal_cpc = self.calculate_breakeven_cpc(
                profit_per_unit, estimated_conversion_rate, target_roas=2.0
            )
            max_recommended_cpc = self.calculate_breakeven_cpc(
                profit_per_unit, estimated_conversion_rate, target_roas=3.0
            )

            # 50円刻みのシナリオを生成
            cpc_range = []
            current = max(50, int(breakeven_cpc / 2))
            max_cpc = int(max_recommended_cpc * 1.5)
            while current <= max_cpc:
                cpc_range.append(current)
                current += 50

        scenarios = []
        for cpc in cpc_range:
            profit_data = self.calculate_monthly_profit_at_cpc(
                cpc, monthly_clicks, profit_per_unit, estimated_conversion_rate
            )
            scenarios.append(
                {
                    "cpc": cpc,
                    **profit_data,
                    "performance_level": self._evaluate_performance(
                        profit_data["roas"], profit_data["net_profit"]
                    ),
                }
            )

        return scenarios

    def _evaluate_performance(self, roas: float, net_profit: float) -> str:
        """パフォーマンスレベルを評価"""
        if net_profit < 0:
            return "赤字"
        elif roas < 1.5:
            return "要改善"
        elif roas < 2.5:
            return "改善中"
        elif roas < 4.0:
            return "良好"
        else:
            return "優秀"

    def get_product_simulator(
        self, product_sku: str, monthly_clicks: int, estimated_conversion_rate: float = 1.0
    ) -> Dict[str, Any]:
        """
        特定商品のシミュレータ情報を取得

        Args:
            product_sku: 商品SKU
            monthly_clicks: 月間クリック数
            estimated_conversion_rate: 推定成約率（%）

        Returns:
            {
                'product_info': {...},
                'key_metrics': {...},
                'scenarios': [...],
                'recommendations': [...],
            }
        """
        if product_sku not in self.products:
            return {
                "error": f"SKU {product_sku} が見つかりません",
                "available_skus": list(self.products.keys()),
            }

        product = self.products[product_sku]
        profit_per_unit = product.get("profit_per_unit", 0)

        breakeven_cpc = self.calculate_breakeven_cpc(
            profit_per_unit, estimated_conversion_rate, target_roas=1.0
        )
        ideal_cpc = self.calculate_breakeven_cpc(
            profit_per_unit, estimated_conversion_rate, target_roas=2.0
        )
        max_recommended_cpc = self.calculate_breakeven_cpc(
            profit_per_unit, estimated_conversion_rate, target_roas=3.0
        )

        scenarios = self.simulate_cpc_scenarios(
            monthly_clicks, profit_per_unit, estimated_conversion_rate
        )

        # 推奨入札額でのシミュレーション
        ideal_profit = self.calculate_monthly_profit_at_cpc(
            ideal_cpc, monthly_clicks, profit_per_unit, estimated_conversion_rate
        )

        recommendations = [
            f"💰 1本の利益: {profit_per_unit:,.0f}円",
            f"📊 推定成約率: {estimated_conversion_rate}%",
            f"🎯 理想的なCPC: {ideal_cpc:.0f}円/クリック",
            f"   └→ ROAS {ideal_profit['roas']}, 月間利益 {ideal_profit['net_profit']:,.0f}円",
            f"⚠️ 最大許容CPC（赤字回避）: {breakeven_cpc:.0f}円/クリック",
            f"⭐ 最大推奨CPC（品質維持）: {max_recommended_cpc:.0f}円/クリック",
            f"✅ 現在の月間クリック数: {monthly_clicks}",
        ]

        return {
            "product_info": {
                "sku": product_sku,
                "name": product.get("name", ""),
                "price": product.get("price", 0),
                "cost": product.get("cost", 0),
                "profit_per_unit": profit_per_unit,
            },
            "key_metrics": {
                "breakeven_cpc": round(breakeven_cpc, 0),
                "ideal_cpc": round(ideal_cpc, 0),
                "max_recommended_cpc": round(max_recommended_cpc, 0),
            },
            "scenarios": scenarios,
            "ideal_profit_scenario": ideal_profit,
            "recommendations": recommendations,
        }

    def compare_products(
        self, monthly_clicks: int, estimated_conversion_rate: float = 1.0
    ) -> Dict[str, Any]:
        """
        複数商品の入札戦略を比較

        Args:
            monthly_clicks: 月間クリック数
            estimated_conversion_rate: 推定成約率（%）

        Returns:
            {
                'product_comparisons': [
                    {
                        'sku': str,
                        'name': str,
                        'ideal_cpc': float,
                        'ideal_monthly_profit': float,
                        'rank': int,
                    },
                    ...
                ],
                'summary': {...},
            }
        """
        comparisons = []

        for sku, product in self.products.items():
            profit_per_unit = product.get("profit_per_unit", 0)
            ideal_cpc = self.calculate_breakeven_cpc(
                profit_per_unit, estimated_conversion_rate, target_roas=2.0
            )
            ideal_profit = self.calculate_monthly_profit_at_cpc(
                ideal_cpc, monthly_clicks, profit_per_unit, estimated_conversion_rate
            )

            comparisons.append(
                {
                    "sku": sku,
                    "name": product.get("name", ""),
                    "profit_per_unit": profit_per_unit,
                    "ideal_cpc": ideal_cpc,
                    "ideal_monthly_profit": ideal_profit["net_profit"],
                    "ideal_roas": ideal_profit["roas"],
                }
            )

        # 利益で降順ソート
        comparisons = sorted(
            comparisons, key=lambda x: x["ideal_monthly_profit"], reverse=True
        )
        for i, comp in enumerate(comparisons, 1):
            comp["rank"] = i

        total_profit = sum(c["ideal_monthly_profit"] for c in comparisons)

        return {
            "product_comparisons": comparisons,
            "summary": {
                "total_products": len(comparisons),
                "total_potential_profit": round(total_profit, 0),
                "average_ideal_cpc": round(
                    sum(c["ideal_cpc"] for c in comparisons) / len(comparisons), 0
                ),
            },
        }
