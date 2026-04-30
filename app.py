"""
Amazon広告運用・意思決定支援ツール
Streamlit ダッシュボード メインアプリケーション
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# パスを設定してローカルモジュールを import
sys.path.insert(0, str(Path(__file__).parent))

from config.config import (
    PAGE_CONFIG,
    PRODUCTS,
    ROAS_TARGET,
    CPC_TARGET,
    CONVERSION_RATE_TARGET,
    PROMOTION_THRESHOLD,
    EXCLUSION_CLICK_THRESHOLD,
    EXCLUSION_REVENUE_THRESHOLD,
)
from src.api import AmazonAdsAPI
from src.analysis import DiagnosticsAnalyzer, KeywordAdvisor, BidSimulator
from src.utils import (
    format_currency,
    format_percentage,
    format_ratio,
    get_score_color,
    get_recommendation_emoji,
    generate_action_todos,
)
from src.utils.data_handler import DataHandler
from src.utils.sheets_handler import SheetsHandler

# =====================
# ページ設定
# =====================
st.set_page_config(**PAGE_CONFIG)

# サイドバースタイル設定
st.markdown(
    """
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .metric-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .score-good { color: #28A745; }
    .score-warning { color: #FFC107; }
    .score-danger { color: #DC3545; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================
# マニュアルターゲティング分析
# =====================
def _show_manual_keyword_analysis(keywords, advisor):
    """マニュアルターゲティング向け入札最適化表示"""
    roas_target = advisor.config.get("ROAS_TARGET", {})
    ideal_roas = roas_target.get("ideal", 4.0)
    min_roas = roas_target.get("min", 2.0)

    bid_up, bid_down, monitor = [], [], []
    for kw in keywords:
        cost = kw.get("cost", 0)
        sales = kw.get("sales", 0)
        clicks = kw.get("clicks", 0)
        conversions = kw.get("conversions", 0)
        roas = sales / cost if cost > 0 else 0
        cpc = cost / clicks if clicks > 0 else 0
        cr = conversions / clicks * 100 if clicks > 0 else 0
        kw_info = {**kw, "roas": roas, "cpc": cpc, "cr": cr}
        if roas >= ideal_roas and clicks > 10:
            bid_up.append(kw_info)
        elif clicks >= 30 and roas < min_roas:
            bid_down.append(kw_info)
        else:
            monitor.append(kw_info)

    col1, col2, col3 = st.columns(3)
    col1.metric("📈 入札強化候補", len(bid_up))
    col2.metric("📉 入札削減・停止候補", len(bid_down))
    col3.metric("👁️ 要監視", len(monitor))

    st.subheader("📈 入札強化候補（ROASが高く、さらに伸ばせる）")
    if bid_up:
        for kw in sorted(bid_up, key=lambda x: x["roas"], reverse=True):
            with st.expander(f"✅ {kw['keyword']} — ROAS {kw['roas']:.1f} / CPC {kw['cpc']:.0f}円"):
                st.write(f"💰 売上: {format_currency(kw.get('sales',0))} ／ 広告費: {format_currency(kw.get('cost',0))}")
                st.write(f"🖱️ クリック: {kw.get('clicks',0)} ／ 成約率: {kw['cr']:.1f}%")
                st.write(f"**推奨アクション**: 入札単価を現在の {kw['cpc']:.0f}円 から **{kw['cpc']*1.2:.0f}〜{kw['cpc']*1.5:.0f}円** に引き上げて表示回数を拡大してください")
    else:
        st.info("入札強化候補はありません")

    st.subheader("📉 入札削減・停止候補（クリックが多いのにROASが低い）")
    if bid_down:
        for kw in sorted(bid_down, key=lambda x: x["cpc"], reverse=True):
            with st.expander(f"⚠️ {kw['keyword']} — ROAS {kw['roas']:.1f} / CPC {kw['cpc']:.0f}円"):
                waste = kw.get("cost", 0)
                st.write(f"💸 広告費: {format_currency(waste)} ／ 売上: {format_currency(kw.get('sales',0))}")
                st.write(f"🖱️ クリック: {kw.get('clicks',0)} ／ 成約率: {kw['cr']:.1f}%")
                if kw["roas"] < 0.5:
                    st.write(f"**推奨アクション**: ROASが極めて低いため、このキーワードを **一時停止** してください")
                else:
                    st.write(f"**推奨アクション**: 入札単価を現在の {kw['cpc']:.0f}円 から **{kw['cpc']*0.6:.0f}〜{kw['cpc']*0.8:.0f}円** に引き下げてROASを改善してください")
    else:
        st.info("入札削減候補はありません")

    st.subheader("👁️ 要監視（データ蓄積中）")
    if monitor:
        mon_df = pd.DataFrame([
            {"キーワード": k["keyword"], "クリック": k.get("clicks",0),
             "ROAS": f"{k['roas']:.1f}", "CPC(円)": f"{k['cpc']:.0f}",
             "マッチタイプ": k.get("matchType", "")}
            for k in monitor[:20]
        ])
        st.dataframe(mon_df, use_container_width=True, hide_index=True)


# =====================
# セッションの初期化
# =====================
@st.cache_resource
def initialize_api():
    """APIクライアントを初期化"""
    return AmazonAdsAPI(
        client_id="",
        client_secret="",
        refresh_token="",
        profile_id="",
        use_mock_data=True,  # デモモード有効
    )


@st.cache_resource
def initialize_analyzers():
    """分析ツールを初期化"""
    config = {
        "ROAS_TARGET": ROAS_TARGET,
        "CPC_TARGET": CPC_TARGET,
        "CONVERSION_RATE_TARGET": CONVERSION_RATE_TARGET,
        "PROMOTION_THRESHOLD": PROMOTION_THRESHOLD,
        "EXCLUSION_CLICK_THRESHOLD": EXCLUSION_CLICK_THRESHOLD,
        "EXCLUSION_REVENUE_THRESHOLD": EXCLUSION_REVENUE_THRESHOLD,
    }

    return {
        "diagnostics": DiagnosticsAnalyzer(config),
        "keyword_advisor": KeywordAdvisor(config),
        "bid_simulator": BidSimulator(PRODUCTS),
    }


# =====================
# Google Sheets 初期化
# =====================
@st.cache_resource
def get_sheets_handler():
    try:
        creds = dict(st.secrets["gcp_service_account"])
        # Streamlit SecretsのTOML経由で\nがエスケープされるため修正
        if "private_key" in creds:
            creds["private_key"] = creds["private_key"].replace("\\n", "\n")
        spreadsheet_id = st.secrets["SPREADSHEET_ID"]
        return SheetsHandler(spreadsheet_id, creds)
    except Exception as e:
        return str(e)

# =====================
# セッション状態の初期化
# =====================
if "uploaded_campaigns" not in st.session_state:
    st.session_state.uploaded_campaigns = None

if "uploaded_keywords" not in st.session_state:
    st.session_state.uploaded_keywords = None

if "sheets_loaded" not in st.session_state:
    st.session_state.sheets_loaded = False

def _get_sheets():
    """SheetsHandlerを返す。エラーまたは未設定の場合はNone"""
    result = get_sheets_handler()
    return result if isinstance(result, SheetsHandler) else None

# 初回のみ Google Sheets からデータを復元
if not st.session_state.sheets_loaded:
    _sh = _get_sheets()
    if _sh:
        try:
            _campaigns = _sh.load_campaigns()
            _keywords = _sh.load_keywords()
            _products = _sh.load_products() if hasattr(_sh, "load_products") else []
            if _campaigns:
                st.session_state.uploaded_campaigns = _campaigns
            if _keywords:
                st.session_state.uploaded_keywords = _keywords
            if _products:
                st.session_state.custom_products = {p["sku"]: p for p in _products}
        except Exception as e:
            st.session_state._sheets_load_error = str(e)
    st.session_state.sheets_loaded = True

if "custom_products" not in st.session_state:
    st.session_state.custom_products = {}


# =====================
# ヘッダー
# =====================
st.title("📊 Amazon広告運用・意思決定支援ツール")
st.markdown(
    """
    高単価焼酎の広告運用を最適化するための3つの機能を提供します。
    - ✅ **診断機能**: 現在の広告設定が適正範囲内かをスコアリング
    - 🚀 **キーワード昇格**: オートで売れたキーワードをマニュアルに昇格
    - 💰 **入札シミュレーター**: 利益から逆算した最適入札額を可視化
    """
)

# =====================
# サイドバー設定
# =====================
st.sidebar.title("⚙️ 設定")

# API設定（デモモード）
with st.sidebar.expander("🔌 API設定", expanded=False):
    st.write("**現在はデモモードで実行中です**")
    st.write("本番運用時は以下の認証情報を入力してください：")
    client_id = st.text_input("Client ID", type="password")
    client_secret = st.text_input("Client Secret", type="password")
    refresh_token = st.text_input("Refresh Token", type="password")
    profile_id = st.text_input("Profile ID")

    if st.button("API接続テスト"):
        st.info("✅ デモモードで実行中のため、テストデータを使用します。")

# データ期間設定
st.sidebar.markdown("---")
st.sidebar.subheader("📅 分析期間")

period_option = st.sidebar.radio(
    "分析期間を選択",
    ["直近30日", "直近60日", "直近90日", "カスタム"],
)

if period_option == "カスタム":
    start_date = st.sidebar.date_input("開始日")
    end_date = st.sidebar.date_input("終了日")
else:
    days_map = {"直近30日": 30, "直近60日": 60, "直近90日": 90}
    days = days_map[period_option]
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

st.sidebar.info(f"分析期間: {start_date} ～ {end_date}")

# =====================
# データ管理
# =====================
st.sidebar.markdown("---")
with st.sidebar.expander("📤 データ管理 - CSVアップロード", expanded=False):
    st.write("**実際のデータをアップロードしてください**")

    upload_type = st.radio(
        "アップロードするデータ",
        ["キャンペーンデータ", "キーワードデータ", "両方"],
    )

    if upload_type in ["キャンペーンデータ", "両方"]:
        st.subheader("1️⃣ キャンペーンデータ")

        # テンプレートダウンロード
        template_campaigns = DataHandler.export_template_campaigns_csv()
        st.download_button(
            label="📥 テンプレートをダウンロード",
            data=template_campaigns,
            file_name="campaign_template.csv",
            mime="text/csv",
        )

        st.caption(
            "必須カラム: campaignId, campaignName, impressions, clicks, cost, conversions, sales"
        )

        campaigns_file = st.file_uploader(
            "キャンペーンCSV/スペース区切りファイルをアップロード", type=["csv", "txt"], key="campaigns_upload"
        )

        if campaigns_file:
            try:
                campaigns_data = DataHandler.read_csv_campaigns(campaigns_file)
                if DataHandler.validate_campaign_data(campaigns_data):
                    st.session_state.uploaded_campaigns = campaigns_data
                    _sheets = get_sheets_handler()
                    if _sheets:
                        _sheets.save_campaigns(campaigns_data)
                    st.success(f"✅ {len(campaigns_data)}個のキャンペーンを保存しました")
                else:
                    st.error("❌ データが不正です")
            except Exception as e:
                st.error(f"❌ エラー: {str(e)}")

    if upload_type in ["キーワードデータ", "両方"]:
        st.subheader("2️⃣ キーワードデータ")

        # テンプレートダウンロード
        template_keywords = DataHandler.export_template_keywords_csv()
        st.download_button(
            label="📥 テンプレートをダウンロード",
            data=template_keywords,
            file_name="keyword_template.csv",
            mime="text/csv",
        )

        st.caption(
            "必須カラム: campaignId, keyword, impressions, clicks, cost, conversions, sales"
        )

        keywords_file = st.file_uploader(
            "キーワードCSV/スペース区切りファイルをアップロード", type=["csv", "txt"], key="keywords_upload"
        )

        if keywords_file:
            try:
                keywords_data = DataHandler.read_csv_keywords(keywords_file)
                if DataHandler.validate_keyword_data(keywords_data):
                    st.session_state.uploaded_keywords = keywords_data
                    _sheets = get_sheets_handler()
                    if _sheets:
                        _sheets.save_keywords(keywords_data)
                    st.success(f"✅ {len(keywords_data)}個のキーワードを保存しました")
                else:
                    st.error("❌ データが不正です")
            except Exception as e:
                st.error(f"❌ エラー: {str(e)}")

    # アップロード状態表示
    st.markdown("---")
    if st.session_state.uploaded_campaigns:
        st.write(f"✅ キャンペーン: {len(st.session_state.uploaded_campaigns)}件")
    if st.session_state.uploaded_keywords:
        st.write(f"✅ キーワード: {len(st.session_state.uploaded_keywords)}件")

    if st.session_state.uploaded_campaigns or st.session_state.uploaded_keywords:
        if st.button("🗑️ データをリセット"):
            st.session_state.uploaded_campaigns = None
            st.session_state.uploaded_keywords = None
            _sh = _get_sheets()
            if _sh:
                _sh.save_campaigns([])
                _sh.save_keywords([])
            st.rerun()

# Google Sheets 接続ステータス
st.sidebar.markdown("---")
_sh_result = get_sheets_handler()
if isinstance(_sh_result, SheetsHandler):
    st.sidebar.success("☁️ Google Sheets 接続済み")
elif isinstance(_sh_result, str):
    st.sidebar.error(f"⚠️ Sheets 接続エラー: {_sh_result[:80]}")
else:
    st.sidebar.warning("☁️ Google Sheets 未設定")

if st.session_state.get("_sheets_load_error"):
    st.sidebar.error(f"読込エラー: {st.session_state._sheets_load_error[:80]}")

# =====================
# 商品設定
# =====================
st.sidebar.markdown("---")
with st.sidebar.expander("🏪 商品設定", expanded=False):
    st.caption("入札シミュレーターで使う商品情報を登録してください")

    with st.form("product_form", clear_on_submit=True):
        p_sku  = st.text_input("SKU（管理番号）", placeholder="例: SKU001")
        p_name = st.text_input("商品名", placeholder="例: プレミアム焼酎 黒麹")
        p_price  = st.number_input("販売価格（円）", min_value=0, step=1000)
        p_cost   = st.number_input("原価（円）", min_value=0, step=1000)
        if st.form_submit_button("➕ 追加・更新"):
            if p_sku and p_name and p_price > 0 and p_cost >= 0:
                new_product = {
                    "sku": p_sku, "name": p_name,
                    "price": p_price, "cost": p_cost,
                    "profit_per_unit": p_price - p_cost,
                }
                st.session_state.custom_products[p_sku] = new_product
                _sh = _get_sheets()
                if _sh and hasattr(_sh, "save_products"):
                    _sh.save_products(list(st.session_state.custom_products.values()))
                st.success(f"✅ {p_name} を登録しました")
            else:
                st.error("SKU・商品名・価格を入力してください")

    if st.session_state.custom_products:
        st.markdown("**登録済み商品**")
        for sku, p in st.session_state.custom_products.items():
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"{p['name']}（利益 {p['profit_per_unit']:,}円）")
            if col_b.button("削除", key=f"del_{sku}"):
                del st.session_state.custom_products[sku]
                _sh = _get_sheets()
                if _sh and hasattr(_sh, "save_products"):
                    _sh.save_products(list(st.session_state.custom_products.values()))
                st.rerun()

# =====================
# ナビゲーション
# =====================
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "📌 ページ選択",
    [
        "ダッシュボード",
        "1️⃣ 診断機能 - 今の設定、大丈夫？",
        "2️⃣ キーワード昇格・除外アドバイザー",
        "3️⃣ 入札シミュレーター",
        "📚 使い方ガイド",
    ],
)

# =====================
# インスタンス初期化
# =====================
api = initialize_api()
analyzers = initialize_analyzers()

# =====================
# ページコンテンツ
# =====================

if page == "ダッシュボード":
    st.header("📈 ダッシュボード")

    # データ取得
    campaign_performance = st.session_state.uploaded_campaigns
    if not campaign_performance:
        st.info("👈 サイドバーの「データ管理」からCSVをアップロードしてください")
        st.stop()
    campaigns = [
        {"campaignId": c["campaignId"], "name": c.get("campaignName", "")}
        for c in campaign_performance
    ]
    st.caption(f"📤 {len(campaign_performance)}件のキャンペーンデータを表示中")

    if campaign_performance:
        # 概要メトリクス
        col1, col2, col3, col4 = st.columns(4)

        total_cost = sum(c.get("cost", 0) for c in campaign_performance)
        total_sales = sum(c.get("sales", 0) for c in campaign_performance)
        total_clicks = sum(c.get("clicks", 0) for c in campaign_performance)
        total_conversions = sum(c.get("conversions", 0) for c in campaign_performance)
        overall_roas = total_sales / total_cost if total_cost > 0 else 0

        with col1:
            st.metric("📊 総売上", format_currency(total_sales))

        with col2:
            st.metric("💰 広告費", format_currency(total_cost))

        with col3:
            st.metric("🎯 ROAS", format_ratio(overall_roas))

        with col4:
            st.metric("🔗 クリック数", f"{int(total_clicks):,}")

        # TODOセクションを生成
        st.markdown("---")
        st.subheader("✅ 今すぐやるべきTODO")

        # 診断結果を計算
        diagnostics = analyzers["diagnostics"]
        diagnostics_result = diagnostics.diagnose_all_campaigns(campaign_performance)

        # キーワード分析の概要を計算（全キャンペーンのキーワードから）
        keyword_advisor = analyzers["keyword_advisor"]
        all_keywords = []
        for campaign in campaigns:
            keywords = api.get_keywords(campaign["campaignId"])
            all_keywords.extend(keywords)

        keywords_analysis = keyword_advisor.analyze_keyword_portfolio(all_keywords)

        # TODOを生成
        todos = generate_action_todos(diagnostics_result, keywords_analysis)

        if todos:
            # TODOカードを表示
            for idx, todo in enumerate(todos, 1):
                with st.container():
                    col_priority, col_content = st.columns([0.8, 9.2])

                    with col_priority:
                        st.write(todo["status"])

                    with col_content:
                        st.markdown(
                            f"""
                            <div style='background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4;'>
                                <strong style='font-size: 0.95rem;'>{idx}. {todo['action']}</strong><br/>
                                <span style='font-weight: bold; font-size: 1rem; color: #222; display: block; margin-top: 0.4rem;'>{todo.get('metrics', '')}</span>
                                <span style='color: #444; font-size: 0.88rem; display: block; margin-top: 0.3rem;'>{todo.get('action_detail', '')}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            # TODOサマリー
            todo_categories = {}
            for todo in todos:
                category = todo["category"]
                todo_categories[category] = todo_categories.get(category, 0) + 1

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📝 総TODO数", len(todos))
            with col2:
                st.metric("🔴 緊急", sum(1 for t in todos if t["priority"] == 1))
            with col3:
                st.metric("📊 カテゴリ", len(todo_categories))

        else:
            st.success("✨ やるべきことがありません！素晴らしい状態です。")

        # キャンペーン別パフォーマンス
        st.markdown("---")
        st.subheader("📋 キャンペーン別パフォーマンス")

        performance_df = pd.DataFrame(campaign_performance)
        performance_df["CPC"] = (performance_df["cost"] / performance_df["clicks"]).round(
            0
        )
        performance_df["成約率%"] = (
            (performance_df["conversions"] / performance_df["clicks"] * 100).round(2)
        )
        performance_df["ROAS"] = (performance_df["sales"] / performance_df["cost"]).round(2)

        # 表示用にカラムを整理
        display_df = performance_df[
            ["campaignName", "impressions", "clicks", "cost", "conversions", "sales", "CPC", "成約率%", "ROAS"]
        ].copy()
        display_df.columns = [
            "キャンペーン",
            "インプレッション",
            "クリック",
            "広告費(円)",
            "成約数",
            "売上(円)",
            "CPC(円)",
            "成約率(%)",
            "ROAS",
        ]

        st.dataframe(display_df, use_container_width=True)

        # グラフ表示
        col1, col2 = st.columns(2)

        with col1:
            fig_roas = px.bar(
                performance_df,
                x="campaignName",
                y="roas" if "roas" in performance_df.columns else "sales",
                title="キャンペーン別ROAS",
                labels={"roas": "ROAS", "campaignName": "キャンペーン"},
                color="roas" if "roas" in performance_df.columns else "sales",
            )
            st.plotly_chart(fig_roas, use_container_width=True)

        with col2:
            fig_sales = px.pie(
                performance_df,
                values="sales",
                names="campaignName",
                title="売上シェア",
            )
            st.plotly_chart(fig_sales, use_container_width=True)

    else:
        st.warning("⚠️ キャンペーンデータを取得できません。API設定を確認してください。")


elif page == "1️⃣ 診断機能 - 今の設定、大丈夫？":
    st.header("🔍 診断機能 - 現在の広告設定診断")

    st.markdown(
        """
    このページでは、あなたの広告設定（ROAS、CPC、成約率）が高単価商材として
    適正範囲内かを診断します。スコアリングにより、改善すべき点を明確にします。
    """
    )

    # キャンペーン診断
    campaign_performance = st.session_state.uploaded_campaigns
    if not campaign_performance:
        st.info("👈 サイドバーの「データ管理」からCSVをアップロードしてください")
        st.stop()

    if campaign_performance:
        diagnostics = analyzers["diagnostics"]
        results = diagnostics.diagnose_all_campaigns(campaign_performance)

        # サマリー
        st.subheader("📊 診断サマリー")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            avg_score = results["summary"]["average_score"]
            st.metric(
                "総合スコア",
                f"{avg_score:.1f} / 100",
                delta=f"{get_score_color(int(avg_score))}",
            )

        with col2:
            high_count = len(results["summary"]["high_performers"])
            st.metric("✅ 良好なキャンペーン", high_count)

        with col3:
            low_count = len(results["summary"]["low_performers"])
            st.metric("⚠️ 要改善キャンペーン", low_count)

        with col4:
            total_campaigns = results["summary"]["total_campaigns"]
            st.metric("📈 総キャンペーン数", total_campaigns)

        # 詳細診断
        st.subheader("📋 キャンペーン別詳細診断")

        for diagnosis in results["diagnoses"]:
            with st.expander(
                f"{get_score_color(diagnosis['overall_score'])} {diagnosis['campaign_name']} (スコア: {diagnosis['overall_score']}/100)",
                expanded=True if diagnosis["overall_score"] < 60 else False,
            ):
                # スコアバー
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "ROAS スコア",
                        f"{diagnosis['scores']['roas']['score']}/100",
                    )
                    st.caption(
                        f"実績: {diagnosis['metrics']['roas']}x (評価: {diagnosis['scores']['roas']['evaluation']})"
                    )

                with col2:
                    st.metric(
                        "CPC スコア",
                        f"{diagnosis['scores']['cpc']['score']}/100",
                    )
                    st.caption(
                        f"実績: {format_currency(diagnosis['metrics']['cpc'])} (評価: {diagnosis['scores']['cpc']['evaluation']})"
                    )

                with col3:
                    st.metric(
                        "成約率 スコア",
                        f"{diagnosis['scores']['conversion_rate']['score']}/100",
                    )
                    st.caption(
                        f"実績: {format_percentage(diagnosis['metrics']['conversion_rate'])} (評価: {diagnosis['scores']['conversion_rate']['evaluation']})"
                    )

                # 詳細メトリクス
                metrics_df = pd.DataFrame(
                    [
                        {"指標": "インプレッション", "値": f"{int(diagnosis['metrics']['impressions']):,}"},
                        {"指標": "クリック", "値": f"{int(diagnosis['metrics']['clicks']):,}"},
                        {"指標": "広告費", "値": format_currency(diagnosis["metrics"]["cost"])},
                        {"指標": "成約数", "値": f"{int(diagnosis['metrics']['conversions'])}"},
                        {"指標": "売上", "値": format_currency(diagnosis["metrics"]["sales"])},
                    ]
                )
                st.dataframe(metrics_df, use_container_width=True, hide_index=True)

                # 改善提案
                st.markdown("#### 💡 改善提案")
                for rec in diagnosis["recommendations"]:
                    st.write(rec)

    else:
        st.warning("⚠️ キャンペーンデータを取得できません。")


elif page == "2️⃣ キーワード昇格・除外アドバイザー":
    st.header("🎯 キーワード昇格・除外アドバイザー")

    st.markdown(
        """
    このページでは、キーワードを3つのカテゴリに分類し、具体的なアクションを提案します：
    - 🚀 **昇格候補**: オートで売れたキーワード → マニュアルに追加
    - 🚫 **除外候補**: クリックが多いのに売上がないキーワード
    - 👁️ **要監視**: その他のキーワード
    """
    )

    # キャンペーン選択
    if not st.session_state.uploaded_campaigns:
        st.info("👈 サイドバーの「データ管理」からCSVをアップロードしてください")
        st.stop()

    campaigns = [
        {"campaignId": c["campaignId"], "name": c.get("campaignName", "")}
        for c in st.session_state.uploaded_campaigns
    ]
    campaign_names = [c["name"] for c in campaigns]
    selected_campaign_idx = st.selectbox(
        "📌 キャンペーンを選択", range(len(campaign_names)), format_func=lambda i: campaign_names[i]
    )
    selected_campaign = campaigns[selected_campaign_idx]

    # キーワード取得
    if st.session_state.uploaded_keywords:
        keywords = [
            k for k in st.session_state.uploaded_keywords
            if str(k.get("campaignId")) == str(selected_campaign["campaignId"])
        ]
        st.caption(f"📤 このキャンペーンのキーワード: {len(keywords)}件")
    else:
        keywords = []

    if keywords:
        advisor = analyzers["keyword_advisor"]

        # マニュアル / オート判定
        auto_types = {"auto", "close-match", "loose-match", "substitutes", "complements", ""}
        is_manual = any(
            str(k.get("matchType", "")).lower() not in auto_types
            for k in keywords
        )

        if is_manual:
            st.info("📋 このキャンペーンはマニュアルターゲティングです。入札最適化の提案を表示します。")
            _show_manual_keyword_analysis(keywords, advisor)
            st.stop()

        analysis = advisor.analyze_keyword_portfolio(keywords)

        # ポートフォリオ分析サマリー
        st.subheader("📊 ポートフォリオ分析")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "🚀 昇格候補",
                analysis["opportunities"]["promotion_candidates"],
                f"売上: {format_currency(analysis['opportunities']['promotion_sales'])}",
            )

        with col2:
            st.metric(
                "🚫 除外候補",
                analysis["opportunities"]["exclusion_candidates"],
                f"無駄: {format_currency(analysis['opportunities']['exclusion_cost_waste'])}",
            )

        with col3:
            st.metric(
                "👁️ 要監視",
                analysis["opportunities"]["monitoring_count"],
            )

        with col4:
            st.metric(
                "💰 全体ROAS",
                f"{format_ratio(analysis['total_analysis']['overall_roas'])}",
            )

        # 昇格候補
        st.subheader("🚀 昇格候補キーワード")
        promotion_keywords = analysis["classified_keywords"]["promotion"]

        if promotion_keywords:
            for kw in promotion_keywords:
                with st.expander(
                    f"✅ {kw['keyword']} - 売上: {format_currency(kw.get('sales', 0))}",
                    expanded=False,
                ):
                    advice = advisor.generate_promotion_advice(kw)
                    for action in advice["recommended_actions"]:
                        st.write(action)

                    # 推定インパクト
                    st.markdown("#### 📈 昇格による推定インパクト")
                    impact_df = pd.DataFrame(
                        [
                            {
                                "指標": "売上増加率",
                                "値": f"{advice['estimated_impact']['estimated_sales_increase_pct']}%",
                            },
                            {
                                "指標": "推定追加売上",
                                "値": format_currency(advice["estimated_impact"]["estimated_additional_revenue"]),
                            },
                            {
                                "指標": "推定追加コスト",
                                "値": format_currency(advice["estimated_impact"]["estimated_additional_cost"]),
                            },
                            {
                                "指標": "推定純利益増加",
                                "値": format_currency(advice["estimated_impact"]["estimated_net_profit_increase"]),
                            },
                        ]
                    )
                    st.dataframe(impact_df, use_container_width=True, hide_index=True)
        else:
            st.info("昇格候補キーワードはありません。")

        # 除外候補
        st.subheader("🚫 除外候補キーワード")
        exclusion_keywords = analysis["classified_keywords"]["exclusion"]

        if exclusion_keywords:
            for kw in exclusion_keywords:
                with st.expander(
                    f"❌ {kw['keyword']} - クリック: {int(kw.get('clicks', 0))}, 売上: {format_currency(kw.get('sales', 0))}",
                    expanded=False,
                ):
                    advice = advisor.generate_exclusion_advice(kw)
                    for action in advice["recommended_actions"]:
                        st.write(action)

                    # 削減効果
                    st.markdown("#### 💸 除外による削減効果")
                    savings_df = pd.DataFrame(
                        [
                            {
                                "指標": "月間無駄コスト",
                                "値": format_currency(advice["expected_savings"]["cost_waste_monthly"]),
                            },
                            {
                                "指標": "年間無駄コスト",
                                "値": format_currency(advice["expected_savings"]["cost_waste_annual"]),
                            },
                        ]
                    )
                    st.dataframe(savings_df, use_container_width=True, hide_index=True)
        else:
            st.info("除外候補キーワードはありません。")

        # 要監視キーワード
        st.subheader("👁️ 要監視キーワード")
        monitoring_keywords = analysis["classified_keywords"]["monitoring"]

        if monitoring_keywords:
            monitoring_df = pd.DataFrame(
                [
                    {
                        "キーワード": kw["keyword"],
                        "クリック": int(kw.get("clicks", 0)),
                        "売上(円)": int(kw.get("sales", 0)),
                        "成約数": int(kw.get("conversions", 0)),
                    }
                    for kw in monitoring_keywords[:10]  # Top 10を表示
                ]
            )
            st.dataframe(monitoring_df, use_container_width=True)
        else:
            st.info("要監視キーワードはありません。")

    else:
        st.warning("⚠️ キーワードデータを取得できません。")


elif page == "3️⃣ 入札シミュレーター":
    st.header("💰 高単価専用・入札シミュレーター")

    st.markdown(
        """
    1本売れた時の利益額から逆算して、「1クリックいくらまでなら損しないか」を
    可視化します。最適な入札戦略をシミュレーションできます。
    """
    )

    # 商品選択（カスタム設定 > config.pyのデモ商品）
    st.subheader("📦 商品選択")
    active_products = st.session_state.custom_products if st.session_state.custom_products else PRODUCTS
    if not st.session_state.custom_products:
        st.info("👈 サイドバーの「商品設定」から実際の商品を登録してください（現在はデモ商品を表示中）")
    product_skus = list(active_products.keys())
    product_names = [f"{active_products[sku]['name']} ({sku})" for sku in product_skus]
    selected_product_idx = st.selectbox(
        "商品を選択", range(len(product_skus)), format_func=lambda i: product_names[i]
    )
    selected_product_sku = product_skus[selected_product_idx]

    # パラメータ設定
    col1, col2, col3 = st.columns(3)

    with col1:
        monthly_clicks = st.number_input(
            "月間クリック数 (想定)",
            min_value=50,
            max_value=10000,
            value=500,
            step=50,
        )

    with col2:
        estimated_cr = st.number_input(
            "推定成約率 (%)",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
        )

    with col3:
        st.empty()

    # シミュレーション実行（カスタム商品設定を使う）
    simulator = BidSimulator(active_products)
    result = simulator.get_product_simulator(
        selected_product_sku, monthly_clicks, estimated_cr
    )

    if "error" not in result:
        # 商品情報
        product_info = result["product_info"]
        st.markdown("#### 📊 商品情報")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("商品名", product_info["name"][:15])
        with col2:
            st.metric("販売価格", format_currency(product_info["price"]))
        with col3:
            st.metric("原価", format_currency(product_info["cost"]))
        with col4:
            st.metric("利益/本", format_currency(product_info["profit_per_unit"]))
        with col5:
            st.metric("利益率", f"{(product_info['profit_per_unit'] / product_info['price'] * 100):.1f}%")

        # 重要な指標
        st.markdown("#### 🎯 入札価格の目安")
        key_metrics = result["key_metrics"]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "🔴 最大許容CPC（赤字回避）",
                f"{key_metrics['breakeven_cpc']:.0f}円/クリック",
            )
            st.caption("これ以上のCPCは赤字になります")

        with col2:
            st.metric(
                "🟡 理想的なCPC",
                f"{key_metrics['ideal_cpc']:.0f}円/クリック",
            )
            st.caption("ROAS 2.0倍を実現")

        with col3:
            st.metric(
                "🟢 最大推奨CPC",
                f"{key_metrics['max_recommended_cpc']:.0f}円/クリック",
            )
            st.caption("ROAS 3.0倍を実現")

        # シナリオシミュレーション
        st.markdown("#### 📈 CPCシナリオ別シミュレーション")

        scenarios = result["scenarios"]
        scenarios_df = pd.DataFrame(scenarios)
        scenarios_df_display = scenarios_df[
            ["cpc", "total_cost", "conversions", "total_profit_from_sales", "net_profit", "roas", "performance_level"]
        ].copy()
        scenarios_df_display.columns = [
            "CPC(円)",
            "月間広告費(円)",
            "推定成約数",
            "売上利益(円)",
            "純利益(円)",
            "ROAS",
            "評価",
        ]

        # パフォーマンスレベルで色付け
        def color_performance(val):
            if val == "赤字":
                return "background-color: #FFE5E5"
            elif val == "要改善":
                return "background-color: #FFF3CD"
            elif val == "改善中":
                return "background-color: #D1ECF1"
            elif val == "良好":
                return "background-color: #D4EDDA"
            else:
                return "background-color: #C8E6C9"

        styled_df = scenarios_df_display.style.map(
            color_performance, subset=["評価"]
        )
        st.dataframe(styled_df, use_container_width=True)

        # グラフ表示
        col1, col2 = st.columns(2)

        with col1:
            fig_profit = px.line(
                scenarios_df,
                x="cpc",
                y="net_profit",
                title="CPC別 月間純利益",
                labels={"cpc": "CPC (円)", "net_profit": "純利益 (円)"},
            )
            fig_profit.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_profit, use_container_width=True)

        with col2:
            fig_roas = px.line(
                scenarios_df,
                x="cpc",
                y="roas",
                title="CPC別 ROAS",
                labels={"cpc": "CPC (円)", "roas": "ROAS"},
            )
            fig_roas.add_hline(y=2.0, line_dash="dash", line_color="orange", annotation_text="目標ROAS 2.0x")
            st.plotly_chart(fig_roas, use_container_width=True)

        # 推奨事項
        st.markdown("#### 💡 推奨事項")
        for rec in result["recommendations"]:
            st.write(rec)

        # 理想シナリオ詳細
        with st.expander("📊 理想シナリオ詳細（ROAS 2.0倍）"):
            ideal_scenario = result["ideal_profit_scenario"]
            scenario_items = [
                ("推奨CPC", f"{key_metrics['ideal_cpc']:.0f}円/クリック"),
                ("月間クリック数（仮定）", f"{monthly_clicks:,}"),
                ("月間広告費", format_currency(ideal_scenario["total_cost"])),
                ("推定成約数", f"{ideal_scenario['conversions']}本"),
                ("推定売上利益", format_currency(ideal_scenario["total_profit_from_sales"])),
                ("純利益（広告費控除後）", format_currency(ideal_scenario["net_profit"])),
                ("ROAS", f"{ideal_scenario['roas']:.2f}倍"),
            ]

            for label, value in scenario_items:
                st.write(f"**{label}**: {value}")

        # 複数商品の比較
        st.markdown("---")
        st.markdown("#### 🏆 全商品の入札戦略比較")

        comparison = simulator.compare_products(monthly_clicks, estimated_cr)
        comparison_df = pd.DataFrame(comparison["product_comparisons"])
        comparison_display = comparison_df[
            ["rank", "sku", "name", "profit_per_unit", "ideal_cpc", "ideal_monthly_profit", "ideal_roas"]
        ].copy()
        comparison_display.columns = [
            "ランク",
            "SKU",
            "商品名",
            "利益/本",
            "理想的なCPC",
            "月間利益",
            "ROAS",
        ]

        st.dataframe(comparison_display, use_container_width=True)

    else:
        st.error(result["error"])


elif page == "📚 使い方ガイド":
    st.header("📚 使い方ガイド")

    st.markdown(
        """
    ## はじめに

    このツールは、Amazon広告を運用する初心者向けの意思決定支援ツールです。
    以下の3つの主要機能で、あなたの広告運用を最適化します。

    ---

    ## 📤 実際のデータをアップロードする

    ### デモモードから本番へ

    デフォルトではデモデータが表示されていますが、実際のAmazon広告データをアップロードして使用できます。

    ### クイックスタート

    1. **左サイドバーを開く** > **📤 データ管理 - CSVアップロード**
    2. **テンプレートをダウンロード** (CSVファイル)
    3. Excelやスプレッドシートであなたのデータを入力
    4. **CSVで保存** (カンマ区切り)
    5. **ツールにアップロード**
    6. **📊 アップロードしたデータを使う** をクリック

    ### 必要なデータ

    **キャンペーンデータ:**
    - campaignId, campaignName, impressions, clicks, cost, conversions, sales

    **キーワードデータ:**
    - campaignId, keyword, impressions, clicks, cost, conversions, sales

    ### データの取得方法

    1. **Amazon Seller Central にログイン**
    2. **広告 > 広告コンソール**
    3. **レポート** からダウンロード
    4. 上記の必須カラムが含まれていることを確認
    5. CSVに変換してアップロード

    ### 詳細ガイド

    📖 [DATA_UPLOAD_GUIDE.md](./DATA_UPLOAD_GUIDE.md) を参照

    ---

    ## 1️⃣ 診断機能 - 「今の設定、大丈夫？」

    **何ができるのか？**
    - 現在の広告設定（ROAS、CPC、成約率）が適正範囲内かを診断
    - スコアリング（0～100点）で改善状況を可視化
    - 具体的な改善提案を自動生成

    **使い方：**
    1. 左サイドバーで分析期間を選択
    2. 「診断機能」ページを開く
    3. キャンペーンごとのスコアを確認
    4. 「要改善」キャンペーンの提案に従って改善

    **見るべきポイント：**
    - 総合スコア: 70以上が目安
    - ROAS 目標: 2.0倍以上（高単価商材）
    - CPC: 最大500円以下
    - 成約率: 1～2%以上

    ---

    ## 2️⃣ キーワード昇格・除外アドバイザー

    **何ができるのか？**
    - キーワードを3つのカテゴリに自動分類
    - 🚀 **昇格候補**: オートで売れたキーワード → マニュアルに追加すべき
    - 🚫 **除外候補**: クリックが多いのに売上がないキーワード → 除外すべき
    - 👁️ **要監視**: その他のキーワード

    **使い方：**
    1. 「キーワード昇格・除外アドバイザー」ページを開く
    2. キャンペーンを選択
    3. 昇格候補・除外候補を確認
    4. 推奨事項に従ってキーワードを調整

    **具体的なアクション：**
    - 🚀 昇格候補は、マニュアル広告に追加して入札額を上げる
    - 🚫 除外候補は、除外キーワードリストに追加する
    - 👁️ 要監視は、今後の成績を見守る

    ---

    ## 3️⃣ 入札シミュレーター

    **何ができるのか？**
    - 1本売れた時の利益額から逆算して最適入札額を計算
    - 「1クリックいくらまでなら損しないか」を可視化
    - 複数のCPCシナリオを比較

    **使い方：**
    1. 「入札シミュレーター」ページを開く
    2. 商品を選択
    3. 月間クリック数と推定成約率を入力
    4. CPC別の利益シミュレーションを確認

    **見るべきポイント：**
    - 🔴 最大許容CPC: これ以上は赤字になる
    - 🟡 理想的なCPC: ROAS 2.0倍を実現
    - 🟢 最大推奨CPC: 余裕を持った運用
    - 月間純利益: 実際の利益を確認

    ---

    ## 🎯 実践的な使用例

    ### 例1: 低パフォーマンスキャンペーンを改善したい
    1. 診断機能でスコアが低いキャンペーンを特定
    2. 改善提案を確認
    3. キーワード昇格・除外アドバイザーで、除外すべきキーワードを見つける
    4. キーワードを除外してCPCを最適化

    ### 例2: 昇格すべきキーワードを見つけたい
    1. キーワード昇格・除外アドバイザーを開く
    2. 昇格候補リストを確認
    3. 入札シミュレーターでCPCを決める
    4. マニュアル広告に昇格

    ### 例3: 新しい商品を追加したい場合のCPC計算
    1. 入札シミュレーターで新商品を選択
    2. 想定クリック数と成約率を入力
    3. 理想的なCPCを確認して入札額を決定

    ---

    ## ⚙️ 設定について

    ### API接続
    - **デモモード**: デフォルトで有効（テストデータで動作確認可能）
    - **本番運用**: Amazon Ads APIの認証情報を入力して接続

    ### 分析期間
    - 左サイドバーで「直近30日」「直近60日」「直近90日」から選択
    - 「カスタム」で任意の期間を設定可能

    ---

    ## 💡 ベストプラクティス

    1. **定期的に診断する**: 週1回は診断機能で現在の状態を確認
    2. **キーワード最適化は継続的**: 昇格・除外アドバイザーを定期的にチェック
    3. **入札戦略は柔軟に**: 季節性やトレンドに応じてCPCを調整
    4. **ROAS 2.0倍以上を維持**: これが高単価商材の目安

    ---

    ## 🆘 トラブルシューティング

    **Q: データが取得できません**
    - A: デモモードの場合、テストデータが自動表示されます
    - A: 本番運用の場合は、API設定を確認してください

    **Q: シミュレーションの結果が現実と異なります**
    - A: 推定成約率をより正確な値に調整してください
    - A: 実績データを蓄積して、パラメータを更新してください

    **Q: どのくらいの頻度で確認すればよい？**
    - A: 最低週1回は診断機能で確認
    - A: 大きな改善を実施した場合は、翌日に効果を確認

    ---

    ## 📞 サポート

    質問や問題があれば、本ツールの開発者にお問い合わせください。
    """
    )

st.sidebar.markdown("---")
st.sidebar.info(
    "**Version 1.0** | 🔒 デモモード実行中 | "
    "本番運用時はAPI認証情報を入力してください"
)
