# checkSIGNAL v2 — Streamlit Cloud デプロイ版

iPhone対応・日本株 / 米国株対応（IRBANK + Alpha Vantage + yfinance）

## ファイル構成

```
checkSIGNAL/
├── streamlit_app.py        # エントリポイント
├── requirements.txt        # 依存ライブラリ
├── .streamlit/
│   └── config.toml         # ダークテーマ設定
└── app/
    ├── main.py             # UI（iPhone最適化）
    └── modules/
        ├── data_fetch.py   # データ取得（IRBANK / Alpha Vantage / yfinance）
        ├── indicators.py   # テクニカル指標計算
        ├── t_logic.py      # タイミングロジック
        ├── q_logic.py      # 質スコアロジック
        ├── q_correction.py # セクター補正
        └── valuation.py    # バリュエーションスコア
```

## Streamlit Cloud デプロイ手順

### 1. GitHub にプッシュ

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_NAME/checkSIGNAL.git
git push -u origin main
```

### 2. Streamlit Cloud でデプロイ

1. https://share.streamlit.io にアクセス
2. "New app" → リポジトリ・ブランチ・Main file (`streamlit_app.py`) を指定
3. **"Advanced settings" → "Secrets"** に以下を入力：

```toml
ALPHA_VANTAGE_API_KEY = "あなたのAPIキー"
```

> Alpha Vantage 無料キーの取得: https://www.alphavantage.co/support/#api-key

4. "Deploy" をクリック → 数分でURLが発行される

## 対応銘柄と取得元

| 入力例 | ファンダ取得元 |
|---|---|
| `7203`（トヨタ） | IRBANK スクレイピング |
| `8306.T`（三菱UFJ） | IRBANK スクレイピング |
| `AAPL`（Apple） | Alpha Vantage OVERVIEW API |
| `MSFT`（Microsoft） | Alpha Vantage OVERVIEW API |

※ Alpha Vantage キー未設定でも米国株のテクニカル分析は動作します。
　 ファンダメンタル（PER/ROE等）は yfinance からの取得にフォールバックします。

## ローカル動作確認

```bash
pip install -r requirements.txt
# .streamlit/secrets.toml を作成
echo 'ALPHA_VANTAGE_API_KEY = "YOUR_KEY"' > .streamlit/secrets.toml
streamlit run streamlit_app.py
```

# 📊 checkSIGNALs — バックテスト用データ書出しツール

任意の銘柄リスト × 任意の日付リストに対して、日次の **QVTスコア・株価データをCSVに書き出す** Jupyter Notebook ツール。

---

## ディレクトリ構成

```
checkSIGNALs/                           ← リポジトリルート
│
├── backtest_export.ipynb               ★ バックテストノートブック（本ツール）
├── dates.csv                           ★ 取得対象日付リスト（YYYYMMDD形式）
│
├── output/                             ★ CSV出力先（自動生成）
│   ├── 202501067203T.csv               　 日本株の例: YYYYMMDD + 4桁コード + T
│   ├── 20250106AAPL_.csv               　 米国株の例: YYYYMMDD + ティッカー5桁
│   └── ...
│
├── app/                                　 Streamlitアプリ本体
│   ├── modules/                        　 スコア計算コアモジュール（既存・変更不要）
│   │   ├── __init__.py
│   │   ├── data_fetch.py               　 株価・ファンダメンタル取得
│   │   ├── indicators.py               　 テクニカル指標 + QVT統合
│   │   ├── q_logic.py                  　 Qスコア（ビジネスの質）
│   │   ├── valuation.py                　 Vスコア（バリュエーション）
│   │   ├── t_logic.py                  　 Tスコア（タイミング）
│   │   ├── q_correction.py             　 Qスコアのセクター補正
│   │   └── pattern_db.py               　 セクター相対評価DB
│   └── data/
│       ├── tse_master_latest.csv       　 TSE銘柄マスター（業種情報）
│       └── industry_thresholds.csv     　 業種別閾値DB
│
├── check_signal.py                     　 StreamlitアプリのEntrypoint
└── requirements.txt
```

> `output/` フォルダは `.gitignore` に追加することを推奨。

---

## セットアップ

```bash
pip install -r requirements.txt
```

追加で必要なパッケージ（`requirements.txt` に未記載の場合）:

```bash
pip install yfinance pandas numpy jupyter
```

---

## 使い方

### 1. `dates.csv` を用意する

取得したい取引日を **1行1日付・YYYYMMDD形式・ヘッダーなし** で記述する。

```
20250106
20250107
20250108
20250109
20250110
```

- 順番はバラバラでも可（内部でソートされる）
- 休場日・祝日は含めない（含めても `-` が出力されるだけでエラーにはならない）
- 東証カレンダー: https://www.jpx.co.jp/corporate/about-jpx/calendar/

### 2. `backtest_export.ipynb` のセル1を編集する

```python
# ▼ 銘柄リスト（最大30銘柄）
TICKERS = [
    "7203.T",  # トヨタ
    "9984.T",  # ソフトバンクG
    "AAPL",    # Apple
    # ...最大30銘柄
]

# ▼ 日付リストCSVのパス
DATES_CSV = "dates.csv"

# ▼ CSV出力先フォルダ
OUTPUT_DIR = "output"

# ▼ 既存CSVを上書きするか（False = 差分のみ追記）
OVERWRITE = True
```

### 3. 「すべて実行」する

Jupyter Notebook でノートブックを開き、**「すべてのセルを実行」** するだけ。

---

## セル構成

| セル | 役割 | 編集 |
|------|------|------|
| セル1 | 設定（銘柄・日付CSV・出力先） | **ここだけ編集** |
| セル2 | インポート・モジュール読み込み | 不要 |
| セル3 | ユーティリティ関数定義 | 不要 |
| セル4 | 四半期キャッシュ管理 | 不要 |
| セル5 | メイン実行（取得 → 計算 → CSV出力） | 不要 |
| セル6 | 出力CSVのプレビュー確認 | 不要 |

---

## 処理フロー

```
dates.csv 読み込み
    ↓
ソート → 四半期境界を事前検出（2024-Q4 / 2025-Q1 など）
    ↓
[1/3] ファンダメンタル取得（四半期 × 銘柄 = 必要分だけ）
      ※ yfinanceは現在値のみ提供のため、四半期ごとに再フェッチして変化を近似
    ↓
[2/3] OHLCV取得（銘柄ごとに1回、全期間分をまとめて取得）
    ↓
[3/3] 銘柄 × 日付ループ
      ├─ 四半期が変わったらファンダメンタルを切り替え
      ├─ その日のOHLCVをスライスしてテクニカル指標を計算
      ├─ Q / V / T スコアを計算
      └─ YYYYMMDDXXXXX.csv に1行書き出し
```

---

## 出力CSVのフォーマット

### ファイル名規則 `YYYYMMDDXXXXX.csv`

| ティッカー | ファイル名 | 備考 |
|---|---|---|
| `7203.T` | `202501137203T.csv` | 数字4桁 + T（5文字固定） |
| `9984.T` | `202501139984T.csv` | 同上 |
| `GOOGL` | `20250113GOOGL.csv` | 5文字そのまま |
| `AAPL` | `20250113AAPL_.csv` | 4文字 → `_` で補完して5文字 |
| `BRK.B` | `20250113BRKB_.csv` | ピリオド除去 + `_` 補完 |

各ファイルは **ヘッダー + データ1行** の構成（1銘柄 × 1日）。

### 列定義

| 列名 | 内容 |
|------|------|
| `date` | 日付（YYYY-MM-DD） |
| `quarter` | 四半期キー（例: `2025-Q1`） |
| `ticker` | ティッカーシンボル |
| `company_name` | 銘柄名 |
| `close` | 終値 |
| `ma_25` | 25日移動平均 |
| `ma_50` | 50日移動平均 |
| `rsi` | RSI（14日） |
| `high_52w` | 52週高値 |
| `low_52w` | 52週安値 |
| `per` | PER（実績） |
| `pbr` | PBR |
| `q_score` | **Qスコア**（ビジネスの質 0〜100） |
| `q1` | Q1サブスコア（収益性） |
| `q3` | Q3サブスコア（財務健全性） |
| `v_score` | **Vスコア**（バリュエーション 0〜100） |
| `v1` | V1: PER/PBR絶対評価 |
| `v2` | V2: EV/EBITDA |
| `v3` | V3: 配当利回り |
| `t_score` | **Tスコア**（タイミング 0〜100） |
| `qvt_score` | **(Q+V+T)/3 総合スコア** |
| `timing_label` | タイミング判定テキスト |
| `signal_text` | 押し目シグナルテキスト |
| `roe` | ROE（%）※四半期値 |
| `roa` | ROA（%）※四半期値 |
| `equity_ratio` | 自己資本比率（%） |
| `operating_margin` | 営業利益率（%） |
| `de_ratio` | D/Eレシオ |
| `interest_coverage` | インタレストカバレッジ |
| `ev_ebitda` | EV/EBITDA |
| `industry` | 業種 |
| `sector` | セクター |

データが存在しない場合（休場・取得失敗）は `-` が入る。

---

## 四半期キャッシュの仕組み

ファンダメンタル指標（ROE・ROA・EV/EBITDAなど）は四半期ごとに1回だけ取得し、同じ四半期内の日付ループでは取得済みの値を再利用する。

```
2024-Q4（10/1〜12/31）のデータ → 2024年10〜12月の日付で使用
2025-Q1（1/1〜3/31）のデータ  → 2025年1〜3月の日付で使用
```

これによりAPI呼び出し回数を最小化しつつ、決算発表サイクルに近い精度でファンダメンタルを反映できる。

---

## 注意事項

- **ファンダメンタルは現在値の近似**: yfinance は過去時点のファンダメンタルを提供しないため、四半期ごとに再フェッチした現在値で代替している。厳密な過去値が必要な場合は別途データソースが必要。
- **Streamlit 不要**: 本ツールはJupyter Notebook単体で動作する。既存のStreamlitアプリ（`check_signal.py`）には一切変更を加えない。
- **最大30銘柄**: `TICKERS` リストの上限は30銘柄を推奨（API負荷・処理時間の観点から）。


