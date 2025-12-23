# -*- coding: utf-8 -*-
import streamlit as st
import anthropic
import pandas as pd
from datetime import datetime
import hmac
import os
import csv
import re

# ページ設定
st.set_page_config(
    page_title="マーケティング予算最適化AI v2.0",
    page_icon="📊",
    layout="wide"
)

# カスタムCSS（ビジネスライク）
st.markdown("""
<style>
    /* メインコンテナ */
    .main {
        background-color: #f8f9fa;
    }
    
    /* カードスタイル */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    
    /* セクションヘッダー */
    .section-header {
        color: #1f2937;
        font-weight: 600;
        margin-top: 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid #e5e7eb;
    }
    
    /* テーブルスタイル */
    .dataframe {
        border: none !important;
    }
    
    /* ボタンスタイル */
    .stButton>button {
        background-color: #2563eb;
        color: white;
        border-radius: 6px;
        padding: 10px 24px;
        font-weight: 500;
    }
    
    .stButton>button:hover {
        background-color: #1d4ed8;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# ステップ3: アクセスログ記録機能
# ============================================

def ensure_log_directory():
    """ログディレクトリの作成"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir

def log_access(username, action, details=""):
    """アクセスログの記録"""
    try:
        log_dir = ensure_log_directory()
        log_file = os.path.join(log_dir, "access_log.csv")
        
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "username": username,
            "display_name": st.session_state.get("user_display_name", username),
            "action": action,
            "details": details
        }
        
        file_exists = os.path.isfile(log_file)
        
        with open(log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "username", "display_name", "action", "details"])
            if not file_exists:
                writer.writeheader()
            writer.writerow(log_entry)
            
    except Exception as e:
        print(f"ログ記録エラー: {e}")

def get_access_logs():
    """アクセスログの取得"""
    log_file = os.path.join("logs", "access_log.csv")
    
    if os.path.exists(log_file):
        try:
            df = pd.read_csv(log_file)
            return df
        except Exception as e:
            st.error(f"ログファイルの読み込みに失敗しました: {e}")
            return None
    else:
        return None

# ============================================
# ステップ2: ユーザー別パスワード認証
# ============================================

def check_password():
    """ユーザー名とパスワードによる認証"""
    
    def login_form():
        """ログインフォームの表示"""
        st.title("マーケティング予算最適化AI")
        st.info("KRAFTON Japan 社内ツールです。ユーザー名とパスワードを入力してください。")
        
        with st.form("login_form"):
            username = st.text_input("ユーザー名", key="username_input")
            password = st.text_input("パスワード", type="password", key="password_input")
            submit = st.form_submit_button("ログイン", type="primary", use_container_width=True)
            
            if submit:
                if "users" in st.secrets:
                    users = st.secrets["users"]
                    
                    if username in users:
                        correct_password = users[username]["password"]
                        
                        if hmac.compare_digest(password, correct_password):
                            st.session_state["password_correct"] = True
                            st.session_state["username"] = username
                            st.session_state["user_display_name"] = users[username].get("display_name", username)
                            
                            log_access(username, "login", "ログイン成功")
                            
                            st.rerun()
                        else:
                            st.error("パスワードが間違っています")
                            log_access(username, "login_failed", "パスワード不一致")
                    else:
                        st.error("ユーザー名が見つかりません")
                        log_access(username, "login_failed", "ユーザー名不明")
                else:
                    st.warning("ユーザー設定が見つかりません。デフォルト認証を使用します。")
                    if username == "admin" and password == "krafton2024":
                        st.session_state["password_correct"] = True
                        st.session_state["username"] = username
                        st.session_state["user_display_name"] = "管理者"
                        
                        log_access(username, "login", "ログイン成功（デフォルト認証）")
                        
                        st.rerun()
                    else:
                        st.error("ユーザー名またはパスワードが間違っています")
        
    #   with st.expander("テスト用アカウント情報"):
    #       st.caption("Secretsが未設定の場合、以下でログインできます：")
    #       st.code("ユーザー名: admin\nパスワード: krafton2024")

    if "password_correct" not in st.session_state:
        login_form()
        return False
    elif not st.session_state["password_correct"]:
        login_form()
        return False
    else:
        return True

# パスワード認証をチェック
if not check_password():
    st.stop()

# ============================================
# 結果パース関数（新規追加）
# ============================================

def parse_markdown_table(markdown_text):
    """マークダウン表をDataFrameに変換"""
    lines = markdown_text.strip().split('\n')
    
    if len(lines) < 2:
        return None
    
    # ヘッダー行を取得
    headers = [h.strip() for h in lines[0].split('|') if h.strip()]
    
    # データ行を取得（区切り線をスキップ）
    data_rows = []
    for line in lines[2:]:
        if line.strip():
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) == len(headers):
                data_rows.append(cells)
    
    if data_rows:
        return pd.DataFrame(data_rows, columns=headers)
    return None

def extract_metrics_from_text(text):
    """テキストから主要メトリクスを抽出"""
    metrics = {}
    
    # 総計を抽出
    total_match = re.search(r'総計.*?(\d+,?\d*)\s*万円', text)
    if total_match:
        metrics['総予算'] = total_match.group(1) + '万円'
    
    # 期待販売本数を抽出
    sales_match = re.search(r'期待販売本数.*?(\d+,?\d*)\s*本', text)
    if sales_match:
        metrics['期待販売本数'] = sales_match.group(1) + '本'
    
    # ROIを抽出
    roi_match = re.search(r'想定ROI.*?(\d+)', text)
    if roi_match:
        metrics['想定ROI'] = roi_match.group(1) + '%'
    
    return metrics

def parse_analysis_result(result_text):
    """分析結果をセクションごとに分割"""
    sections = {}
    current_section = None
    current_content = []
    
    for line in result_text.split('\n'):
        # セクションヘッダーを検出（## で始まる行）
        if line.startswith('## '):
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = line.replace('## ', '').strip()
            current_content = []
        elif line.startswith('### '):
            # サブセクションもコンテンツに含める
            current_content.append(line)
        else:
            current_content.append(line)
    
    # 最後のセクションを追加
    if current_section:
        sections[current_section] = '\n'.join(current_content)
    
    return sections

# ============================================
# ここから通常のアプリコード
# ============================================

# ログインユーザー情報の表示
with st.sidebar:
    st.success(f"ログイン中: {st.session_state.get('user_display_name', 'ゲスト')}")
    
    if st.button("ログアウト", use_container_width=True):
        log_access(
            st.session_state.get("username", "unknown"),
            "logout",
            "ログアウト"
        )
        
        st.session_state["password_correct"] = False
        if "username" in st.session_state:
            del st.session_state["username"]
        if "user_display_name" in st.session_state:
            del st.session_state["user_display_name"]
        st.rerun()
    
    st.markdown("---")
    
    # 管理者のみアクセスログ閲覧可能
    if st.session_state.get("username") == "admin":
        with st.expander("アクセスログ（管理者専用）"):
            if st.button("ログを表示", use_container_width=True):
                st.session_state["show_logs"] = True
            
            if st.button("ログを非表示", use_container_width=True):
                st.session_state["show_logs"] = False

# タイトル
st.title("マーケティング予算最適化AI v2.0")
st.caption("実績データに基づく現実的な予算配分案を提案")
st.markdown("---")

# アクセスログ表示（管理者のみ）
if st.session_state.get("show_logs", False) and st.session_state.get("username") == "admin":
    st.subheader("アクセスログ")
    
    logs_df = get_access_logs()
    
    if logs_df is not None and not logs_df.empty:
        logs_df_sorted = logs_df.sort_values("timestamp", ascending=False)
        
        # 統計情報
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("総アクセス数", len(logs_df))
        with col_stat2:
            unique_users = logs_df["username"].nunique()
            st.metric("ユニークユーザー数", unique_users)
        with col_stat3:
            login_count = len(logs_df[logs_df["action"] == "login"])
            st.metric("ログイン回数", login_count)
        
        st.dataframe(
            logs_df_sorted,
            use_container_width=True,
            height=300
        )
        
        csv_data = logs_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="ログをCSVでダウンロード",
            data=csv_data,
            file_name=f"access_log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.info("まだアクセスログがありません")
    
    st.markdown("---")

# サイドバー: APIキー入力
with st.sidebar:
    st.header("設定")
    
    if "ANTHROPIC_API_KEY" in st.secrets:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.success("APIキー設定済み")
    else:
        api_key = st.text_input("Claude API Key", type="password")
        if api_key:
            st.success("APIキー入力済み")
    
    st.markdown("---")
    st.markdown("### 使い方")
    st.markdown("""
    1. プロジェクト情報を入力
    2. マーケティング施策を選択
    3. 参考データを確認・編集
    4. 分析実行
    """)
    st.markdown("---")
    st.markdown("### v2.0 新機能")
    st.markdown("""
    - 過去実績データ入力
    - 現実的なCPV/ROI予測
    - 実績ベースの見積もり
    """)

# メイン入力フォーム
col1, col2 = st.columns(2)

with col1:
    st.subheader("プロジェクト情報")
    project_name = st.text_input(
        "プロジェクト名",
        value="プSubnautica 2",
        help="ゲームタイトルや製品名"
    )
    
    project_genre = st.text_input(
        "ジャンル",
        value="サバイバル/クラフティング",
        help="ゲームジャンルや製品カテゴリ"
    )
    
    launch_date = st.date_input(
        "ローンチ予定日",
        help="発売日またはキャンペーン開始日"
    )
    
    target_sales = st.number_input(
        "目標販売本数",
        min_value=0,
        value=100000,
        step=10000,
        help="達成したい販売目標"
    )

with col2:
    st.subheader("予算設定")
    total_marketing_budget = st.number_input(
        "総マーケティング予算(万円)",
        min_value=0,
        value=50000,
        step=1000,
        help="使用可能な総マーケティング予算"
    )
    
    campaign_period = st.selectbox(
        "キャンペーン期間",
        ["1ヶ月", "3ヶ月", "6ヶ月", "1年"],
        index=1,
        help="マーケティング活動の期間"
    )
    
    target_market = st.selectbox(
        "主要ターゲット市場",
        ["日本のみ", "日本+アジア", "グローバル"],
        index=0
    )
    
    optimization_focus = st.selectbox(
        "最適化の重点",
        ["認知度最大化", "購買転換率最大化", "ROI最大化", "リーチ最大化"],
        index=2
    )

# マーケティング施策
st.markdown("---")
st.subheader("マーケティング施策候補")

col3, col4 = st.columns(2)

with col3:
    st.markdown("**主要施策**")
    
    use_vtuber = st.checkbox("VTuberマーケティング", value=True)
    use_digital_ads = st.checkbox("デジタル広告", value=True)
    use_events = st.checkbox("イベント・展示会", value=True)
    use_pr = st.checkbox("PR・メディア露出", value=True)
    use_influencer = st.checkbox("インフルエンサー施策", value=True)
    use_community = st.checkbox("コミュニティ施策", value=False)

with col4:
    selected_tactics = []
    
    if use_vtuber:
        vtuber_detail = st.text_input(
            "VTuber施策詳細",
            value="ホロライブ・にじさんじ大手5-10名",
            help="具体的な施策内容"
        )
        selected_tactics.append(f"VTuberマーケティング: {vtuber_detail}")
    
    if use_digital_ads:
        digital_detail = st.text_input(
            "デジタル広告詳細",
            value="YouTube、Twitter、Steam広告",
            help="広告プラットフォーム"
        )
        selected_tactics.append(f"デジタル広告: {digital_detail}")
    
    if use_events:
        events_detail = st.text_input(
            "イベント詳細",
            value="東京ゲームショウ、BitSummit",
            help="出展予定のイベント"
        )
        selected_tactics.append(f"イベント・展示会: {events_detail}")
    
    if use_pr:
        pr_detail = st.text_input(
            "PR施策詳細",
            value="4Gamer、IGN Japan、Famitsu",
            help="ターゲットメディア"
        )
        selected_tactics.append(f"PR・メディア露出: {pr_detail}")
    
    if use_influencer:
        influencer_detail = st.text_input(
            "インフルエンサー詳細",
            value="Twitch、YouTube配信者20-30名",
            help="ターゲットインフルエンサー"
        )
        selected_tactics.append(f"インフルエンサー施策: {influencer_detail}")
    
    if use_community:
        community_detail = st.text_input(
            "コミュニティ施策詳細",
            value="Discord、Reddit、公式フォーラム",
            help="コミュニティ戦略"
        )
        selected_tactics.append(f"コミュニティ施策: {community_detail}")

# 参考データ
st.markdown("---")
st.subheader("参考データ（重要: 実績ベースの見積もりに使用）")

col_ref1, col_ref2 = st.columns(2)

with col_ref1:
    vtuber_reference = st.text_area(
        "VTuber/インフルエンサー施策の参考データ",
        value="""【過去実績データ（Switch向けゲーム）】

■ フォロワー規模別の実績:
- 7万人級: コスト 5-17万円、CPV 0.9-10円、7日視聴 5,600-56,500
- 10万人級: コスト 10-15万円、CPV 6-10円、7日視聴 14,000-25,000
- 25万人級: コスト 17-20万円、CPV 4.9-6円、7日視聴 21,000-34,000
- 47万人級: コスト 220万円、CPV 19円、7日視聴 113,000

■ プラットフォーム別:
- YouTube VOD: CPV 5-20円が一般的
- Twitch Live: CPV 25-27円（PCU 1,700+で27万視聴達成例）

■ コスト構造:
- 直接取引 < 代理店経由（+20-30%）< 事務所経由（+30-50%）
- 大手事務所（THECOO等）所属は単価上昇傾向

■ エンゲージメント:
- 平均ENG率: 0.6-3%
- 平均CTR: 0.13-0.45%
- 平均CPC: 388-11,957円

■ 成長パターン:
- Day1→Day3: 1.2-3倍
- Day1→Day7: 1.8-5倍
- Day1→Day30: 2.5-6倍""",
        height=300,
        help="実際の過去案件データを入力してください"
    )

with col_ref2:
    other_reference = st.text_area(
        "その他施策の参考データ",
        value="""【デジタル広告】
- YouTube広告: CPM 500-1,000円
- Twitter/X広告: CPC 100-300円
- Steam広告: CPM 800-1,500円
- Google Display: CPM 400-800円

【イベント出展】
- 東京ゲームショウ:
  * 小ブース（18㎡）: 500-800万円
  * 中ブース（54㎡）: 1,500-2,000万円
  * 運営費・人件費: +300-500万円
- BitSummit:
  * 基本ブース: 50-100万円
  * 運営費: +50-100万円

【PR・メディア露出】
- 大手メディアタイアップ記事: 300-500万円/1記事
- 中堅メディア記事: 50-150万円/1記事
- プレスリリース配信: 10-30万円
- レビュアー向けコード配布: コストなし（製品原価のみ）

【一般的なKPI目安】
- CVR（認知→購入）: 0.5-2%
- CPA（獲得単価）: 2,000-5,000円
- ROAS: 150-300%が標準的""",
        height=300,
        help="実際の過去実績や市場データを入力"
    )

# 制約条件と追加情報
st.markdown("---")
st.subheader("制約条件・特記事項")

col5, col6 = st.columns(2)

with col5:
    constraints = st.text_area(
        "必須の制約条件",
        height=100,
        placeholder="""例:
VTuberマーケティングは最低40%確保
デジタル広告は25%以上
イベント予算は固定で500万円""",
        help="必ず守るべき予算制約"
    )

with col6:
    additional_context = st.text_area(
        "その他の考慮事項",
        height=100,
        placeholder="""例:
Early Access段階のため段階的な投資が必要
前作ファン10万人への優先アプローチ
日本市場での認知度向上が最優先""",
        help="戦略立案時の背景情報"
    )

# 分析実行ボタン
if st.button("予算最適化を実行", type="primary", use_container_width=True):
    if not api_key:
        st.error("Claude API Keyを入力してください（サイドバー）")
    elif not selected_tactics:
        st.error("最低1つのマーケティング施策を選択してください")
    elif total_marketing_budget <= 0:
        st.error("総マーケティング予算は0より大きい値を入力してください")
    else:
        log_access(
            st.session_state.get("username", "unknown"),
            "analysis_executed",
            f"プロジェクト: {project_name}, 予算: {total_marketing_budget}万円"
        )
        
        with st.spinner("最適化計算中... (30-60秒かかります)"):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                
                tactics_list = "\n".join([f"- {tactic}" for tactic in selected_tactics])
                
                prompt = f"""
あなたはゲームパブリッシングのマーケティング予算最適化の専門家です。以下の情報を基に、最適なマーケティング予算配分案を作成してください。

【プロジェクト情報】
- プロジェクト名: {project_name}
- ジャンル: {project_genre}
- ローンチ予定日: {launch_date}
- 目標販売本数: {target_sales:,}本
- ターゲット市場: {target_market}

【予算情報】
- 総マーケティング予算: {total_marketing_budget:,}万円
- キャンペーン期間: {campaign_period}
- 最適化の重点: {optimization_focus}

【実施予定のマーケティング施策】
{tactics_list}

【参考データ - VTuber/インフルエンサー施策】
{vtuber_reference}

【参考データ - その他施策】
{other_reference}

【制約条件】
{constraints if constraints else "特になし"}

【その他の考慮事項】
{additional_context if additional_context else "特になし"}

**【重要な指示】**
1. **参考データを厳密に遵守**: 上記の参考データに記載されたCPV、CPM、CPC、コスト範囲を絶対に超えないでください
2. **現実的な数値**: フォロワー規模に応じた適切なコストとリーチを算出してください
3. **実績ベースの予測**: 過去の成長率パターン（Day1→Day7で1.8-5倍）を基に計算してください
4. **保守的な見積もり**: 不確実性を考慮し、やや保守的な数値を採用してください
5. **CPV計算**: コスト ÷ 予想視聴数 = CPVが参考データの範囲内であることを確認してください

日本のゲーム市場の特性（VTuber影響力、Steamユーザー層、口コミ重視など）を考慮してください。

以下の形式で回答してください:

## 1. プロジェクト概要と制約の確認
*入力情報の整理と前提条件の確認*

## 2. マーケティング予算配分案（3パターン）

### パターンA: 認知拡大重視プラン
| 施策 | 詳細 | 配分額(万円) | 構成比 | 期待リーチ | CPV/CPM | 配分理由 |
|------|------|-------------|--------|-----------|---------|----------|
| VTuber | 10万人級×5名 | ... | ...% | ... | ...円 | 参考データより10万人級はCPV 6-10円 |
| ... | ... | ... | ...% | ... | ...円 | ... |

**総計**: {total_marketing_budget:,}万円
**期待総視聴数**: ...回
**期待販売本数**: ...本（CVR 0.5-2%で計算）
**想定ROI**: ...%

### パターンB: バランス型プラン（推奨）
| 施策 | 詳細 | 配分額(万円) | 構成比 | 期待リーチ | CPV/CPM | 配分理由 |
|------|------|-------------|--------|-----------|---------|----------|
| ... | ... | ... | ...% | ... | ...円 | ... |

**総計**: {total_marketing_budget:,}万円
**期待総視聴数**: ...回
**期待販売本数**: ...本
**想定ROI**: ...%

### パターンC: 購買転換重視プラン
| 施策 | 詳細 | 配分額(万円) | 構成比 | 期待リーチ | CPV/CPM | 配分理由 |
|------|------|-------------|--------|-----------|---------|----------|
| ... | ... | ... | ...% | ... | ...円 | ... |

**総計**: {total_marketing_budget:,}万円
**期待総視聴数**: ...回
**期待販売本数**: ...本
**想定ROI**: ...%

## 3. 数値の妥当性検証

## 4. タイムライン別予算配分

## 5. KPI設定と測定方法

## 6. リスク分析と対応策

## 7. 推奨実行プラン

## 8. 次のアクション（チェックリスト形式）

## 9. 免責事項
"""
                
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                result = message.content[0].text
                
                st.success("最適化完了")
                st.markdown("---")
                
                # セクションごとに分割
                sections = parse_analysis_result(result)
                
                # タブで結果を整理
                tab1, tab2, tab3 = st.tabs(["最適化結果", "入力サマリー", "ダウンロード"])
                
                with tab1:
                    # 各セクションをexpanderで表示
                    for section_name, section_content in sections.items():
                        with st.expander(section_name, expanded=(section_name.startswith("2."))):
                            # 表が含まれているか確認
                            if '|' in section_content and '---' in section_content:
                                # 表とそれ以外を分離
                                parts = section_content.split('\n\n')
                                for part in parts:
                                    if '|' in part and '---' in part:
                                        # 表をDataFrameに変換
                                        df = parse_markdown_table(part)
                                        if df is not None:
                                            st.dataframe(df, use_container_width=True)
                                    elif part.strip():
                                        # 通常のテキスト
                                        st.markdown(part)
                            else:
                                # 表が含まれていない場合はそのまま表示
                                st.markdown(section_content)
                                
                                # メトリクスを抽出して表示
                                if "パターン" in section_name:
                                    metrics = extract_metrics_from_text(section_content)
                                    if metrics:
                                        cols = st.columns(len(metrics))
                                        for idx, (key, value) in enumerate(metrics.items()):
                                            with cols[idx]:
                                                st.metric(key, value)
                    
                with tab2:
                    st.subheader("入力サマリー")
                    
                    summary_data = {
                        "項目": [
                            "プロジェクト名",
                            "目標販売本数",
                            "総マーケティング予算",
                            "キャンペーン期間",
                            "ターゲット市場",
                            "最適化重点",
                            "選択施策数"
                        ],
                        "内容": [
                            project_name,
                            f"{target_sales:,}本",
                            f"{total_marketing_budget:,}万円",
                            campaign_period,
                            target_market,
                            optimization_focus,
                            str(len(selected_tactics))
                        ]
                    }
                    df_summary = pd.DataFrame(summary_data)
                    st.dataframe(df_summary, use_container_width=True, hide_index=True)
                    
                    st.subheader("選択された施策")
                    tactics_df = pd.DataFrame({
                        "施策": selected_tactics
                    })
                    st.dataframe(tactics_df, use_container_width=True, hide_index=True)
                    
                    st.subheader("使用された参考データ")
                    st.info("VTuber施策: 実績データ入力済み")
                    if other_reference:
                        st.info("その他施策: 実績データ入力済み")
                
                with tab3:
                    st.download_button(
                        label="結果をテキストでダウンロード",
                        data=result,
                        file_name=f"{project_name}_marketing_budget_v2_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain"
                    )
                    
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.info("APIキーが正しいか確認してください")

# フッター
st.markdown("---")
st.caption("マーケティング予算最適化AI v2.0 - KRAFTON Japan Internal Tool")
