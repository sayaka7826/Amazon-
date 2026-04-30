"""
ユーティリティ関数
"""
from typing import Dict, List, Any


def format_currency(value: float) -> str:
    """金額をフォーマット"""
    return f"{value:,.0f}円"


def format_percentage(value: float, decimals: int = 2) -> str:
    """パーセンテージをフォーマット"""
    return f"{value:.{decimals}f}%"


def format_ratio(value: float, decimals: int = 2) -> str:
    """比率をフォーマット"""
    return f"{value:.{decimals}f}倍"


def get_score_color(score: int) -> str:
    """スコアに基づいて色を返す"""
    if score >= 80:
        return "🟢"  # 良好
    elif score >= 60:
        return "🟡"  # 注意
    else:
        return "🔴"  # 要改善


def truncate_text(text: str, max_length: int = 50) -> str:
    """テキストを指定長でトリミング"""
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text


def get_recommendation_emoji(classification: str) -> str:
    """分類に基づいて絵文字を返す"""
    emojis = {
        "promotion": "🚀",
        "exclusion": "🚫",
        "monitoring": "👁️",
    }
    return emojis.get(classification, "")


def generate_action_todos(diagnostics_result: Dict[str, Any], keywords_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    診断結果とキーワード分析からTODOを生成

    Args:
        diagnostics_result: 診断機能の結果
        keywords_analysis: キーワード分析の結果

    Returns:
        優先度付きのTODOリスト
    """
    todos = []

    # 診断結果から低スコアのキャンペーンを抽出
    if diagnostics_result.get("diagnoses"):
        for diagnosis in diagnostics_result["diagnoses"]:
            score = diagnosis.get("overall_score", 100)
            campaign_name = diagnosis.get("campaign_name", "Unknown")
            scores = diagnosis.get("scores", {})
            metrics = diagnosis.get("metrics", {})

            # 問題のある指標を特定
            bad_evals = {"要改善", "改善中"}
            roas_bad = scores.get("roas", {}).get("evaluation") in bad_evals
            cpc_bad = scores.get("cpc", {}).get("evaluation") in bad_evals
            cr_bad = scores.get("conversion_rate", {}).get("evaluation") in bad_evals

            indicator_parts = []
            if roas_bad:
                indicator_parts.append(f"ROAS {metrics.get('roas', 0):.1f}")
            if cpc_bad:
                indicator_parts.append(f"CPC {metrics.get('cpc', 0):.0f}円/クリック")
            if cr_bad:
                indicator_parts.append(f"成約率 {metrics.get('conversion_rate', 0):.1f}%")
            metrics_text = "・".join(indicator_parts) if indicator_parts else "複合的な問題"

            if cpc_bad and roas_bad:
                action_detail = "キャンペーン全体の入札単価を引き下げ、除外KWを追加してCPCとROASを改善してください"
            elif cpc_bad:
                action_detail = "キャンペーン全体の入札単価を引き下げてCPCを削減してください"
            elif roas_bad:
                action_detail = "除外KWを追加して無駄なクリックを削減し、ROASを改善してください"
            elif cr_bad:
                action_detail = "商品ページのタイトル・画像を見直すか、無関係なKWを除外して成約率を改善してください"
            else:
                action_detail = "診断ページで詳細な改善提案を確認してください"

            if score < 50:
                # 重大: スコア50未満
                todos.append(
                    {
                        "priority": 1,
                        "status": "🔴",
                        "action": f"【緊急】{campaign_name} の改善 (スコア: {score}/100)",
                        "metrics": metrics_text,
                        "action_detail": action_detail,
                        "category": "診断",
                    }
                )
            elif score < 70:
                # 中: スコア50～70
                todos.append(
                    {
                        "priority": 2,
                        "status": "🟡",
                        "action": f"{campaign_name} の改善検討 (スコア: {score}/100)",
                        "metrics": metrics_text,
                        "action_detail": action_detail,
                        "category": "診断",
                    }
                )

    # キーワード分析から昇格候補を抽出
    if keywords_analysis.get("opportunities"):
        promotion_count = keywords_analysis["opportunities"].get("promotion_candidates", 0)
        promotion_sales = keywords_analysis["opportunities"].get("promotion_sales", 0)

        if promotion_count > 0:
            promotion_kws = keywords_analysis.get("classified_keywords", {}).get("promotion", [])
            top_kws = [kw.get("keyword", "") for kw in promotion_kws[:3] if kw.get("keyword")]
            kw_text = "・".join(top_kws)
            kw_suffix = f"（他{promotion_count - len(top_kws)}件）" if promotion_count > len(top_kws) else ""
            todos.append(
                {
                    "priority": 2,
                    "status": "🚀",
                    "action": f"{promotion_count}個の昇格候補KWをマニュアル広告に追加",
                    "metrics": f"対象KW: {kw_text}{kw_suffix}　合計売上 {format_currency(promotion_sales)}",
                    "action_detail": "各KWの入札単価をそれぞれのCPC×1.2〜1.5倍に設定し、マニュアル広告キャンペーンに追加してください",
                    "category": "キーワード",
                }
            )

    # キーワード分析から除外候補を抽出
    if keywords_analysis.get("opportunities"):
        exclusion_count = keywords_analysis["opportunities"].get("exclusion_candidates", 0)
        exclusion_waste = keywords_analysis["opportunities"].get("exclusion_cost_waste", 0)

        if exclusion_count > 0:
            exclusion_kws = keywords_analysis.get("classified_keywords", {}).get("exclusion", [])
            top_kws = []
            for kw in exclusion_kws[:3]:
                name = kw.get("keyword", "")
                cost = kw.get("cost", 0)
                if name:
                    top_kws.append(f"{name}（{format_currency(cost)}/月）")
            kw_text = "・".join(top_kws)
            kw_suffix = f"（他{exclusion_count - len(exclusion_kws[:3])}件）" if exclusion_count > 3 else ""
            todos.append(
                {
                    "priority": 2,
                    "status": "🚫",
                    "action": f"{exclusion_count}個の除外候補KWを除外キーワードに登録",
                    "metrics": f"対象KW: {kw_text}{kw_suffix}　削減可能な無駄な広告費 合計 {format_currency(exclusion_waste)}/月",
                    "action_detail": "各KWをキャンペーンの除外キーワードに登録し、無駄なクリック費用を削減してください",
                    "category": "キーワード",
                }
            )

    # スコアが良好でも改善の余地がある場合
    if diagnostics_result.get("summary"):
        avg_score = diagnostics_result["summary"].get("average_score", 100)

        if avg_score < 80:
            todos.append(
                {
                    "priority": 3,
                    "status": "📈",
                    "action": "入札シミュレーターで各KWの適正入札単価（CPC上限）を確認",
                    "metrics": f"キャンペーン平均スコア: {avg_score}/100",
                    "action_detail": "利益目標から逆算した各KWごとのCPC上限を確認し、KW単位で入札単価を調整してください",
                    "category": "最適化",
                }
            )

    # 優先度でソート
    todos = sorted(todos, key=lambda x: x["priority"])

    # ユニークな行動を保つ（重複排除）
    seen = set()
    unique_todos = []
    for todo in todos:
        key = (todo["action"], todo["category"])
        if key not in seen:
            seen.add(key)
            unique_todos.append(todo)

    return unique_todos
