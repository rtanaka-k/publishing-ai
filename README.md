#  マーケティング予算最適化AI v2.0

KRAFTON Japan K.K. 社内ツール  
ゲームパブリッシング向けマーケティング予算配分の最適化支援

##  機能

- **プロジェクト情報入力**: ゲームタイトル、ジャンル、目標販売本数
- **施策選択**: VTuber、デジタル広告、イベント、PR等
- **実績データ参照**: 過去案件のCPV/CPM/CPC実績を基に算出
- **3パターン提案**: 認知拡大/バランス/購買転換の3つの予算配分案
- **数値妥当性検証**: 参考データとの照合による現実性チェック

##  使い方

### オンライン版（推奨）
Streamlit Cloudでデプロイ後にアクセス

### ローカル実行
```bash
# 1. 仮想環境作成
python -m venv venv
venv\Scripts\activate

# 2. パッケージインストール
pip install -r requirements.txt

# 3. 起動
streamlit run marketing_budget_optimizer_v2.py
```

##  セットアップ

### Claude APIキーの取得
1. https://console.anthropic.com/ にアクセス
2. API Keyを作成
3. Streamlit Cloud Secretsに設定

##  必要条件

- Python 3.8以上
- Claude API Key
- インターネット接続

##  セキュリティ

- APIキーは環境変数で管理
- パスワード認証によるアクセス制限
- 入力データは保存されません

##  免責事項

本ツールの分析結果は参考データに基づく推定値です。実際の効果は市場状況により変動します。

##  バージョン

**v2.0** (2024-12-15)
- 実績データ入力機能追加
- 数値妥当性検証機能追加

##  開発者

KRAFTON Japan Publishing Planning
