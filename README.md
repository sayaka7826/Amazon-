# Amazon広告運用・意思決定支援ツール

高単価焼酎（1本2.9万～5.5万円）の売上を最適化するための、AI支援型広告管理ダッシュボード。

## 📋 概要

このツールは、Amazon広告の初心者でも「次の一手」がわかり、着実に成果（売上増）を出すための3つの主要機能を提供します。

### 🎯 主要機能

1. **「今の設定、大丈夫？」診断機能**
   - 既存のオート/マニュアル広告のROAS、CPC、成約率を分析
   - 高単価商材として適正範囲内かをスコアリング
   - 具体的な改善提案を自動生成

2. **キーワード昇格・除外アドバイザー**
   - オートで売れたキーワードを「マニュアルへ追加すべき」と提案
   - 売れないのにクリックが多いキーワードを「除外すべき」と提案

3. **高単価専用・入札シミュレーター**
   - 1本売れた時の利益額から逆算
   - 「1クリックいくらまでなら損しないか」を可視化
   - 複数のCPCシナリオを比較

## 🛠️ 技術スタック

- **言語**: Python 3.8+
- **フレームワーク**: Streamlit（Web UIフレームワーク）
- **分析**: Pandas, NumPy, Plotly
- **API連携**: Amazon Ads API

## 📦 システム要件

- macOS または Linux （Windows対応予定）
- Python 3.8 以上
- pip（Pythonパッケージマネージャー）
- インターネット接続

## 🚀 クイックスタート

### 1. 環境構築

#### ステップ1: Pythonのインストール確認

```bash
python3 --version
```

Python 3.8 以上がインストールされていることを確認してください。

#### ステップ2: プロジェクトディレクトリへ移動

```bash
cd "/Users/sayaka/Documents/claudecodeテスト/Amazon広告分析用ツール"
```

#### ステップ3: 仮想環境の作成（推奨）

Python環境の分離のため、仮想環境を作成します。

**macOSの場合:**

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate
```

**Windows の場合:**

```bash
python -m venv venv
venv\Scripts\activate
```

有効化後、プロンプトの最初に `(venv)` と表示されます。

#### ステップ4: 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

これにより以下がインストールされます：
- streamlit: Webダッシュボード用
- pandas: データ分析用
- plotly: グラフ描画用
- requests: API通信用
- python-dotenv: 環境変数管理用

### 2. デモモードで起動

```bash
streamlit run app.py
```

初回起動時に、ブラウザが自動的に開きます。
ブラウザが開かない場合は、以下のURLにアクセスしてください：
```
http://localhost:8501
```

### 3. 動作確認

- ✅ ダッシュボードページが表示される
- ✅ 診断機能でテストデータが表示される
- ✅ グラフやメトリクスが表示される

これで準備完了です！

## 📖 使用方法

### デモモードでの動作確認

デフォルトではデモモードで動作し、サンプルデータが表示されます。

**デモモードの特徴:**
- Amazon Ads APIに接続しない
- モックデータを自動生成
- すべての機能を試用可能

### 本番運用への移行

Amazon広告に実際に接続するには：

#### ステップ1: `.env` ファイルを作成

プロジェクトのルートに `.env` ファイルを作成します：

```bash
# .env ファイルの内容
AMAZON_CLIENT_ID=your_client_id_here
AMAZON_CLIENT_SECRET=your_client_secret_here
AMAZON_REFRESH_TOKEN=your_refresh_token_here
AMAZON_PROFILE_ID=your_profile_id_here
```

#### ステップ2: Amazon Ads APIの認証情報を取得

1. Amazon Seller Central にログイン
2. 広告 > 広告コンソール
3. API設定から認証情報を取得
4. 上記の `.env` ファイルに入力

#### ステップ3: アプリを再起動

```bash
streamlit run app.py
```

本番モードで起動し、実際の広告データが表示されます。

## 📊 ページ構成

### 📈 ダッシュボード
- キャンペーン別パフォーマンス表示
- ROASチャート
- 売上シェア分析

### 🔍 診断機能
- ROAS、CPC、成約率のスコアリング
- キャンペーン別の詳細診断
- 改善提案の自動生成

### 🎯 キーワード昇格・除外アドバイザー
- キーワードを3つのカテゴリに自動分類
- 昇格・除外候補の具体的理由
- 推定インパクト・削減効果の表示

### 💰 入札シミュレーター
- 利益から逆算した適正入札額の計算
- CPCシナリオ別シミュレーション
- グラフによる可視化

## 🔧 設定ファイル

### `config/config.py`

アプリケーションの設定を管理します：

```python
# 高単価商材の基本情報
PRODUCTS = {
    "SKU001": {
        "name": "プレミアム焼酎 黒麹",
        "price": 29000,
        "cost": 12000,
        "profit_per_unit": 17000,
    },
    # ... その他のSKU
}

# 診断機能の適正範囲
ROAS_TARGET = {
    "min": 2.0,      # 最小（損益分岐点）
    "ideal": 4.0,    # 理想値
    "max": 8.0,      # 最大（非常に良好）
}
```

## 📁 ディレクトリ構造

```
Amazon広告分析用ツール/
├── README.md                   # このファイル
├── requirements.txt            # 依存パッケージリスト
├── app.py                     # Streamlit メインアプリケーション
├── config/
│   └── config.py              # 設定ファイル
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── amazon_ads_api.py # Amazon Ads API 連携
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── diagnostics.py    # 診断機能
│   │   ├── keyword_advisor.py # キーワード昇格・除外
│   │   └── bid_simulator.py  # 入札シミュレーター
│   └── utils/
│       ├── __init__.py
│       └── helpers.py         # ユーティリティ関数
└── data/
    └── sample_data.json       # サンプルデータ
```

## 🎓 使用例

### 例1: 低パフォーマンスキャンペーンを改善

1. **診断機能を開く** → スコアが低いキャンペーンを特定
2. **改善提案を確認** → 具体的なアクションを参照
3. **キーワード昇格・除外アドバイザーを使用** → 除外すべきキーワードを見つける
4. **キーワードを除外** → CPCを最適化

### 例2: 新しいキャンペーンのCPCを決定

1. **入札シミュレーターを開く** → 商品を選択
2. **月間クリック数と成約率を入力** → シミュレーション実行
3. **理想的なCPCを確認** → 入札額を決定

## 🐛 トラブルシューティング

### エラー: `ModuleNotFoundError: No module named 'streamlit'`

**解決策:**
```bash
pip install -r requirements.txt
```

### エラー: `Permission denied` (macOS/Linux)

**解決策:**
```bash
chmod +x app.py
```

### Streamlitが起動しない

**解決策:**
1. 仮想環境が有効化されているか確認
   ```bash
   source venv/bin/activate  # macOS/Linux
   ```

2. すべてのパッケージがインストールされているか確認
   ```bash
   pip list
   ```

### データが表示されない

**確認項目:**
- [ ] 分析期間は正しいか？ → サイドバーで期間を確認
- [ ] デモモードか本番モードか？ → デモモードの場合はテストデータが表示される
- [ ] ネットワーク接続は正常か？ → インターネット接続を確認

## 📝 ログとデバッグ

デバッグ情報は以下で確認できます：

```bash
# ログレベルを設定して起動
streamlit run app.py --logger.level=debug
```

## 🔒 セキュリティ

- **`.env` ファイルは絶対にコミットしないでください** → `.gitignore` に追加
- API認証情報は環境変数で管理
- 本番運用時はHTTPSを使用してください

## 📈 パフォーマンス

**推奨設定:**
- CPU: 2コア以上
- メモリ: 4GB以上
- ブラウザ: Chrome, Firefox, Safari 最新版

## 🌟 ベストプラクティス

1. **定期的に診断する**: 週1回は診断機能で現在の状態を確認
2. **キーワード最適化は継続的**: 昇格・除外アドバイザーを定期的にチェック
3. **入札戦略は柔軟に**: 季節性やトレンドに応じてCPCを調整
4. **ROAS 2.0倍以上を維持**: これが高単価商材の目安

## 🚀 今後の予定

- [ ] クラウド展開（AWS Lambda, Google Cloud等）
- [ ] 機械学習による最適入札予測
- [ ] レポート自動生成機能
- [ ] Slack連携
- [ ] メール通知機能

## 📞 サポート・フィードバック

質問や機能リクエスト、バグ報告は開発者にお問い合わせください。

## 📄 ライセンス

このツールはプライベート用です。

## 📚 参考資料

- [Amazon Ads API ドキュメント](https://advertising.amazon.com/API/docs)
- [Streamlit ドキュメント](https://docs.streamlit.io/)
- [Pandas ドキュメント](https://pandas.pydata.org/docs/)

---

**Version**: 1.0  
**最終更新**: 2026年4月30日  
**開発者**: Claude Code Assistant
# Amazon-
