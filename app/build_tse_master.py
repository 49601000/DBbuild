"""
build_tse_master.py - TSE全銘柄 属性マスタ生成用の軽量バッチ

目的
----
JPXの上場銘柄一覧を母集団として、yfinance を補完ソースに使いながら
TSE全銘柄の属性マスタCSVを生成する。

想定出力
--------
- output/tse_master_latest.csv
- output/tse_master_YYYYMMDD.csv
- output/tse_master_summary_YYYYMMDD.txt
- output/tse_master_meta.json

主なカラム
----------
- ticker
- company_name
- market
- sector
- industry
- internal_category
- financial_type
- notes

使い方
------
Python から:
    from build_tse_master import build_tse_master
    result = build_tse_master(market_scope="all", refresh_pool=False)

CLI から:
    python build_tse_master.py
    python build_tse_master.py --market-scope prime --refresh-pool
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None


# ============================================================
# ルート探索
# ============================================================

def _find_tool_root() -> Path:
    """
    core/ と run.py が両方存在するディレクトリをツールルートとして返す。
    auto_pipeline.py と同じ書き味で、Notebook からもスクリプト実行からも使えるようにする。
    """
    candidates = [Path(__file__).resolve().parent]
    candidates += list(Path(__file__).resolve().parents)

    for p in candidates:
        if (p / "core").is_dir() and (p / "run.py").is_file():
            return p

    for p in sys.path:
        candidate = Path(p)
        if (candidate / "core").is_dir() and (candidate / "run.py").is_file():
            return candidate


    # fallback: 02_データベースbuild (04_qvt最適化ツール用)
    db_build = Path(__file__).resolve().parent.parent.parent / "02_データベースbuild"
    if (db_build / "core").is_dir():
        return db_build

    raise RuntimeError(
        "ツールルートが見つかりません。\n"
        "setup_path.py を先に import してください:\n"
        "  import setup_path\n"
        "  from build_tse_master import build_tse_master"
    )


TOOL_ROOT = _find_tool_root()
_tool_root_str = str(TOOL_ROOT)
if _tool_root_str not in sys.path:
    sys.path.insert(0, _tool_root_str)


# 既存コードベースに依存する処理
try:
    from core.market_pool import (
        fetch_jpx_listed_stocks,
        get_pool_by_market,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "core.market_pool の import に失敗しました。\n"
        "既存プロジェクト構成上にこのファイルを配置してください。"
    ) from exc


logger = logging.getLogger("build_tse_master")


# ============================================================
# 設定
# ============================================================

DEFAULT_OUTPUT_DIR = TOOL_ROOT / "output"
DEFAULT_DATA_DIR = TOOL_ROOT / "app" / "data"
DEFAULT_POOL_CACHE = TOOL_ROOT / "pool" / "jpx_listed_stocks.csv"


@dataclass(slots=True)
class BuildConfig:
    market_scope: str = "all"      # all / prime / standard / growth
    refresh_pool: bool = False
    sleep_sec: float = 0.8
    timeout_sec: int = 20
    use_yfinance: bool = True
    save_csv: bool = True
    output_dir: Path = DEFAULT_OUTPUT_DIR
    data_dir: Path = DEFAULT_DATA_DIR
    latest_filename: str = "tse_master_latest.csv"
    backup_prefix: str = "tse_master"


# ============================================================
# 表示 helper
# ============================================================

def _setup_logger(level: int = logging.INFO) -> None:
    if logger.handlers:
        return
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def _print_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(f"{title}")
    print("=" * 72)


def _print_phase(num: int, title: str) -> None:
    print("\n" + "-" * 72)
    print(f"PHASE {num}: {title}")
    print("-" * 72)


# ============================================================
# 取得・整形
# ============================================================

def normalize_ticker(value: Any) -> str:
    """JPXコードを Yahoo Finance 向け ticker 文字列に正規化する。"""
    if pd.isna(value):
        return ""

    s = str(value).strip()
    if not s:
        return ""

    if s.endswith(".T"):
        return s

    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) >= 4:
        return f"{digits[:4]}.T"

    return s


JPX_MARKET_COL_CANDIDATES = [
    "market", "市場・商品区分", "市場区分", "market_segment"
]
JPX_SECTOR_COL_CANDIDATES = [
    "sector", "33業種区分", "17業種区分", "industry_category"
]
JPX_NAME_COL_CANDIDATES = [
    "company_name", "銘柄名", "name", "issue_name"
]
JPX_CODE_COL_CANDIDATES = [
    "ticker", "code", "コード", "local_code"
]


def _pick_first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def prepare_base_universe(all_stocks: pd.DataFrame, market_scope: str) -> pd.DataFrame:
    """JPX母集団からベース列を整えた DataFrame を返す。"""
    if market_scope == "all":
        df = all_stocks.copy()
    else:
        df = get_pool_by_market(all_stocks, market_scope).copy()

    code_col = _pick_first_existing_column(df, JPX_CODE_COL_CANDIDATES)
    name_col = _pick_first_existing_column(df, JPX_NAME_COL_CANDIDATES)
    market_col = _pick_first_existing_column(df, JPX_MARKET_COL_CANDIDATES)
    sector_col = _pick_first_existing_column(df, JPX_SECTOR_COL_CANDIDATES)

    if code_col is None:
        raise KeyError(
            f"JPX DataFrame に ticker/code 系カラムが見つかりません。columns={list(df.columns)}"
        )

    base = pd.DataFrame()
    base["ticker"] = df[code_col].map(normalize_ticker)
    base["company_name_jpx"] = df[name_col] if name_col else pd.NA
    base["market_jpx"] = df[market_col] if market_col else pd.NA
    base["sector_jpx"] = df[sector_col] if sector_col else pd.NA
    base = base[base["ticker"].astype(bool)].copy()
    base = base.drop_duplicates(subset=["ticker"]).reset_index(drop=True)
    return base


def _safe_fast_info(ticker: str) -> dict[str, Any]:
    if yf is None:
        return {}

    try:
        tk = yf.Ticker(ticker)
        fast = getattr(tk, "fast_info", None)
        if fast is None:
            return {}
        return dict(fast)
    except Exception as exc:
        logger.debug("fast_info failed for %s: %s", ticker, exc)
        return {}


def _safe_info(ticker: str) -> dict[str, Any]:
    if yf is None:
        return {}

    try:
        tk = yf.Ticker(ticker)
        info = getattr(tk, "info", None)
        if not info:
            return {}
        return dict(info)
    except Exception as exc:
        logger.debug("info failed for %s: %s", ticker, exc)
        return {}


def fetch_yfinance_profile(ticker: str, sleep_sec: float = 0.8) -> dict[str, Any]:
    """
    yfinance から company profile 的な最低限の属性を取る。
    取得失敗は空 dict を返す。
    """
    info = _safe_info(ticker)
    fast = _safe_fast_info(ticker)

    row = {
        "ticker": ticker,
        "company_name_yf": info.get("longName") or info.get("shortName") or pd.NA,
        "market_yf": info.get("exchange") or info.get("fullExchangeName") or pd.NA,
        "sector_yf": info.get("sector") or pd.NA,
        "industry_yf": info.get("industry") or pd.NA,
        "quote_type": info.get("quoteType") or pd.NA,
        "currency": info.get("currency") or fast.get("currency") or pd.NA,
        "country": info.get("country") or pd.NA,
        "website": info.get("website") or pd.NA,
        "yf_fetch_status": "ok" if info else "empty",
    }

    if sleep_sec > 0:
        time.sleep(sleep_sec)

    return row


# ============================================================
# 分類ロジック
# ============================================================

def _norm_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def classify_internal_category(
    company_name: Any,
    sector: Any,
    industry: Any,
    quote_type: Any,
) -> str:
    """
    内部カテゴリを返す。

    Returns
    -------
    bank / insurance / leasing / securities / other_financial / non_financial / unknown
    """
    name = _norm_text(company_name)
    sec = _norm_text(sector)
    ind = _norm_text(industry)
    qtype = _norm_text(quote_type)
    text = " | ".join([name, sec, ind, qtype])

    bank_keywords = [
        "bank", "banks", "銀行", "信託", "credit union"
    ]
    insurance_keywords = [
        "insurance", "保険", "life insurance", "property & casualty"
    ]
    leasing_keywords = [
        "lease", "leasing", "リース", "credit", "consumer finance", "ノンバンク"
    ]
    securities_keywords = [
        "securities", "broker", "証券", "asset management", "investment bank"
    ]
    financial_keywords = [
        "financial", "金融", "capital", "financing", "consumer finance", "credit services"
    ]

    if any(k in text for k in bank_keywords):
        return "bank"
    if any(k in text for k in insurance_keywords):
        return "insurance"
    if any(k in text for k in leasing_keywords):
        return "leasing"
    if any(k in text for k in securities_keywords):
        return "securities"
    if any(k in text for k in financial_keywords):
        return "other_financial"

    # ETF / REIT 等を別扱いしたい場合の保険
    if qtype in {"etf", "reit", "fund"}:
        return "unknown"

    if any([name, sec, ind]):
        return "non_financial"

    return "unknown"


def classify_financial_type(internal_category: str, sector: Any, industry: Any) -> str:
    """
    financial_type を軽く付与する。
    必要に応じて既存の apply_financial_type に寄せて拡張可能。
    """
    sec = _norm_text(sector)
    ind = _norm_text(industry)

    if internal_category == "bank":
        if "regional" in ind:
            return "regional_bank"
        if "diversified" in ind or "major" in ind:
            return "major_bank"
        return "bank"

    if internal_category == "insurance":
        if "life" in ind:
            return "life_insurance"
        if "property" in ind or "casualty" in ind:
            return "p_and_c_insurance"
        return "insurance"

    if internal_category == "leasing":
        return "leasing"

    if internal_category == "securities":
        return "securities"

    if internal_category == "other_financial":
        if "asset management" in ind:
            return "asset_management"
        if "consumer finance" in ind:
            return "consumer_finance"
        return "other_financial"

    if "financial" in sec or "金融" in sec:
        return "other_financial"

    return "non_financial"


def build_notes(row: pd.Series) -> str:
    notes: list[str] = []
    if pd.isna(row.get("industry_yf")):
        notes.append("industry_missing")
    if pd.isna(row.get("sector_yf")):
        notes.append("sector_missing")
    if row.get("yf_fetch_status") != "ok":
        notes.append("yfinance_profile_incomplete")
    return "; ".join(notes)


# ============================================================
# マージ・品質
# ============================================================

def finalize_master(base_df: pd.DataFrame, yf_df: pd.DataFrame) -> pd.DataFrame:
    df = base_df.merge(yf_df, on="ticker", how="left")

    df["company_name"] = df["company_name_yf"].combine_first(df["company_name_jpx"])
    df["market"] = df["market_jpx"].combine_first(df["market_yf"])
    df["sector"] = df["sector_jpx"].combine_first(df["sector_yf"])
    df["industry"] = df["industry_yf"]

    df["internal_category"] = df.apply(
        lambda r: classify_internal_category(
            company_name=r.get("company_name"),
            sector=r.get("sector"),
            industry=r.get("industry"),
            quote_type=r.get("quote_type"),
        ),
        axis=1,
    )
    df["financial_type"] = df.apply(
        lambda r: classify_financial_type(
            r.get("internal_category", "unknown"),
            r.get("sector"),
            r.get("industry"),
        ),
        axis=1,
    )
    df["notes"] = df.apply(build_notes, axis=1)

    ordered_cols = [
        "ticker",
        "company_name",
        "market",
        "sector",
        "industry",
        "internal_category",
        "financial_type",
        "notes",
        # raw columns (監査・デバッグ用)
        "company_name_jpx",
        "market_jpx",
        "sector_jpx",
        "company_name_yf",
        "market_yf",
        "sector_yf",
        "industry_yf",
        "quote_type",
        "currency",
        "country",
        "website",
        "yf_fetch_status",
    ]

    existing_cols = [c for c in ordered_cols if c in df.columns]
    remain_cols = [c for c in df.columns if c not in existing_cols]
    df = df[existing_cols + remain_cols].copy()
    return df.sort_values(["market", "ticker"], na_position="last").reset_index(drop=True)


def summarize_master(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(df)),
        "missing_company_name": int(df["company_name"].isna().sum()),
        "missing_sector": int(df["sector"].isna().sum()),
        "missing_industry": int(df["industry"].isna().sum()),
        "internal_category_counts": df["internal_category"].value_counts(dropna=False).to_dict(),
        "financial_type_counts": df["financial_type"].value_counts(dropna=False).to_dict(),
        "market_counts": df["market"].fillna("<NA>").value_counts(dropna=False).to_dict(),
    }


# ============================================================
# 保存
# ============================================================

def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_outputs(df: pd.DataFrame, summary: dict[str, Any], config: BuildConfig) -> dict[str, str]:
    _ensure_dir(config.output_dir)
    _ensure_dir(config.data_dir)

    today = datetime.now().strftime("%Y%m%d")
    latest_output = config.output_dir / config.latest_filename
    backup_output = config.output_dir / f"{config.backup_prefix}_{today}.csv"
    latest_data = config.data_dir / config.latest_filename
    backup_data = config.data_dir / f"{config.backup_prefix}_{today}.csv"
    summary_txt = config.output_dir / f"tse_master_summary_{today}.txt"
    meta_json = config.output_dir / "tse_master_meta.json"

    df.to_csv(latest_output, index=False, encoding="utf-8-sig")
    df.to_csv(backup_output, index=False, encoding="utf-8-sig")
    df.to_csv(latest_data, index=False, encoding="utf-8-sig")
    df.to_csv(backup_data, index=False, encoding="utf-8-sig")

    lines = [
        f"rows: {summary['rows']}",
        f"missing_company_name: {summary['missing_company_name']}",
        f"missing_sector: {summary['missing_sector']}",
        f"missing_industry: {summary['missing_industry']}",
        "",
        "[internal_category_counts]",
    ]
    lines += [f"- {k}: {v}" for k, v in summary["internal_category_counts"].items()]
    lines += ["", "[financial_type_counts]"]
    lines += [f"- {k}: {v}" for k, v in summary["financial_type_counts"].items()]
    lines += ["", "[market_counts]"]
    lines += [f"- {k}: {v}" for k, v in summary["market_counts"].items()]
    summary_txt.write_text("\n".join(lines), encoding="utf-8")

    meta = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tool": "build_tse_master.py",
        "summary": summary,
    }
    meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "latest_output": str(latest_output),
        "backup_output": str(backup_output),
        "latest_data": str(latest_data),
        "backup_data": str(backup_data),
        "summary_txt": str(summary_txt),
        "meta_json": str(meta_json),
    }


# ============================================================
# メイン
# ============================================================

def build_tse_master(
    market_scope: str = "all",
    refresh_pool: bool = False,
    sleep_sec: float = 0.8,
    use_yfinance: bool = True,
    save_csv: bool = True,
    output_dir: str | Path | None = None,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    TSE全銘柄の属性マスタを生成する。

    Parameters
    ----------
    market_scope : str
        all / prime / standard / growth
    refresh_pool : bool
        True の場合、JPXキャッシュを削除して再取得する
    sleep_sec : float
        yfinance 取得間隔
    use_yfinance : bool
        False の場合、JPXベースのみでマスタを作る
    save_csv : bool
        True の場合、CSV / txt / json を保存する
    output_dir : str | Path | None
        保存先 output/ を上書きしたい場合に指定
    data_dir : str | Path | None
        保存先 app/data/ を上書きしたい場合に指定
    """
    _setup_logger()
    start = time.time()

    config = BuildConfig(
        market_scope=market_scope,
        refresh_pool=refresh_pool,
        sleep_sec=sleep_sec,
        use_yfinance=use_yfinance,
        save_csv=save_csv,
        output_dir=Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR,
        data_dir=Path(data_dir) if data_dir else DEFAULT_DATA_DIR,
    )

    _print_header("TSE属性マスタ生成 開始")

    # --------------------------------------------------
    # PHASE 1: JPX母集団取得
    # --------------------------------------------------
    _print_phase(1, "JPX銘柄リスト取得")
    if config.refresh_pool and DEFAULT_POOL_CACHE.exists():
        DEFAULT_POOL_CACHE.unlink()
        logger.info("JPXキャッシュを削除しました（再取得します）")

    all_stocks = fetch_jpx_listed_stocks(save_cache=True)
    if all_stocks.empty:
    
    # fallback: 02_データベースbuild (04_qvt最適化ツール用)
    db_build = Path(__file__).resolve().parent.parent.parent / "02_データベースbuild"
    if (db_build / "core").is_dir():
        return db_build

    raise RuntimeError("JPX銘柄リストの取得に失敗しました。")

    base_df = prepare_base_universe(all_stocks, market_scope=config.market_scope)
    print(f"  対象銘柄数: {len(base_df)} 件 (market_scope={config.market_scope})")

    # --------------------------------------------------
    # PHASE 2: yfinance profile 取得
    # --------------------------------------------------
    _print_phase(2, "yfinance 属性取得")
    rows: list[dict[str, Any]] = []

    if config.use_yfinance:
        total = len(base_df)
        for i, ticker in enumerate(base_df["ticker"].tolist(), start=1):
            if i == 1 or i % 100 == 0 or i == total:
                print(f"  progress: {i:>4}/{total}  {ticker}")
            rows.append(fetch_yfinance_profile(ticker, sleep_sec=config.sleep_sec))
    else:
        rows = [{"ticker": t, "yf_fetch_status": "skipped"} for t in base_df["ticker"].tolist()]

    yf_df = pd.DataFrame(rows)
    print(f"  yfinance rows: {len(yf_df)} 件")

    # --------------------------------------------------
    # PHASE 3: マスタ整形
    # --------------------------------------------------
    _print_phase(3, "マスタ整形・分類")
    master_df = finalize_master(base_df, yf_df)
    summary = summarize_master(master_df)
    print(f"  rows              : {summary['rows']}")
    print(f"  missing industry  : {summary['missing_industry']}")
    print(f"  missing sector    : {summary['missing_sector']}")
    print(f"  missing name      : {summary['missing_company_name']}")

    # --------------------------------------------------
    # PHASE 4: 保存
    # --------------------------------------------------
    saved: dict[str, str] = {}
    if config.save_csv:
        _print_phase(4, "保存")
        saved = save_outputs(master_df, summary, config)
        for k, v in saved.items():
            print(f"  {k}: {v}")

    elapsed = time.time() - start
    print(f"\n完了: {elapsed/60:.1f} 分")

    return {
        "master_df": master_df,
        "summary": summary,
        "saved": saved,
    }


# ============================================================
# CLI
# ============================================================

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TSE全銘柄の属性マスタCSVを生成する")
    parser.add_argument(
        "--market-scope",
        default="all",
        choices=["all", "prime", "standard", "growth"],
        help="対象市場範囲",
    )
    parser.add_argument(
        "--refresh-pool",
        action="store_true",
        help="JPXキャッシュを削除して再取得する",
    )
    parser.add_argument(
        "--sleep-sec",
        type=float,
        default=0.8,
        help="yfinance 取得間隔（秒）",
    )
    parser.add_argument(
        "--no-yfinance",
        action="store_true",
        help="yfinance を使わず JPX ベースのみで生成する",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="ファイル保存をスキップする",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    build_tse_master(
        market_scope=args.market_scope,
        refresh_pool=args.refresh_pool,
        sleep_sec=args.sleep_sec,
        use_yfinance=not args.no_yfinance,
        save_csv=not args.no_save,
    )


if __name__ == "__main__":
    main()
