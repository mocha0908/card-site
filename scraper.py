import argparse
import csv
import math
import os
import platform
import random
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.driver_cache import DriverCacheManager


# =========================
# 設定系（デフォルト）
# =========================
DEFAULT_WAIT_SEC = 12
DEFAULT_RETRY = 2
DEFAULT_DELAY = 1.0  # ページ間待機（秒）
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class Args:
    mode: str
    group_id: Optional[int]
    keyword: str
    start_page: int
    end_page: Optional[int]
    all_pages: bool
    output: Path
    csv_mode: str  # new|append|overwrite
    headful: bool
    delay: float
    retry: int
    wait_sec: int
    rpm: Optional[int]  # requests per minute 的な上限。Noneなら無制限
    checkpoint_every: int  # 何ページごとに中間保存するか（0はしない）
    reset_session_every: int  # 何ページごとにブラウザを再起動するか（0はしない）


# =========================
# ドライバ生成（修正版）
# =========================
def find_chromedriver_executable(base_path: str) -> str:
    """
    macOSでwebdriver-managerが間違ったパスを返す問題を修正
    正しいchromedriver実行ファイルを探す
    """
    base_dir = Path(base_path).parent

    # 可能なchromedriverのファイル名
    possible_files = [
        "chromedriver",
        "chromedriver-mac-arm64",
        "chromedriver-mac-x64",
        "chromedriver.exe"
    ]

    for filename in possible_files:
        candidate = base_dir / filename
        if candidate.exists() and candidate.is_file():
            # 実行可能ファイルか確認（Unix系の場合）
            if platform.system() != "Windows":
                st = candidate.stat()
                if st.st_mode & stat.S_IXUSR:
                    return str(candidate)
            else:
                # Windowsの場合は.exeファイルを優先
                if filename.endswith(".exe"):
                    return str(candidate)

    # 見つからない場合は元のパスを返す
    return base_path


def make_driver(headful: bool) -> webdriver.Chrome:
    options = Options()
    if not headful and not os.environ.get("HEADFUL"):
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")  # 追加：共有メモリ問題対策
    options.add_argument("--window-size=1280,2000")
    options.add_argument("--lang=ja-JP")
    options.add_argument(f"--user-agent={USER_AGENT}")
    # サイレント化（余計なログ抑制）
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    # ChromeDriverのパスを取得
    driver_path = None

    # 1. プロジェクトルートのchromedriverを優先
    local_driver = Path(__file__).parent / "chromedriver"
    if local_driver.exists() and local_driver.is_file():
        # 実行権限があるか確認
        st = local_driver.stat()
        if platform.system() != "Windows" and not (st.st_mode & stat.S_IXUSR):
            print(f"⚠️ {local_driver} に実行権限がありません。権限を付与します...")
            local_driver.chmod(st.st_mode | stat.S_IXUSR)
        driver_path = str(local_driver)
        print(f"Using local ChromeDriver: {driver_path}")

    # 2. ローカルになければwebdriver-managerを使用
    if not driver_path:
        try:
            driver_path = ChromeDriverManager().install()
            # macOSの場合、正しい実行ファイルパスを探す
            if platform.system() == "Darwin":
                driver_path = find_chromedriver_executable(driver_path)
            print(f"Using ChromeDriver from webdriver-manager: {driver_path}")
        except Exception as e:
            print(f"❌ ChromeDriverの自動インストールに失敗: {e}")
            print("手動でChromeDriverをプロジェクトルートに配置してください。")
            print("参考: https://chromedriver.chromium.org/downloads")
            raise

    try:
        driver = webdriver.Chrome(service=Service(driver_path), options=options)
    except Exception as e:
        print(f"❌ ChromeDriverの起動に失敗: {e}")
        raise

    return driver


# =========================
# URLビルダ
# =========================
def build_group_url(group_id: int, page: int) -> str:
    base = f"https://www.cardrush-pokemon.jp/product-group/{group_id}"
    return f"{base}?page={page}"


def build_search_url(page: int, keyword: str, num: int = 100, img: int = 160) -> str:
    base = "https://www.cardrush-pokemon.jp/product-list"
    query = {"keyword": keyword, "Submit": "検索", "num": str(num), "img": str(img), "page": page}
    return f"{base}?{urlencode(query)}"


# =========================
# パース補助
# =========================
def extract_text(soup: BeautifulSoup, selector: str, default: str = "") -> str:
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else default


def extract_image_url(soup: BeautifulSoup) -> str:
    img = soup.select_one("img")
    if not img:
        return ""
    return img.get("data-x2") or img.get("src", "") or ""


def extract_product_id(soup: BeautifulSoup) -> str:
    # 1) input.open_modal_window_product_form の data-id
    tag = soup.select_one("input.open_modal_window_product_form")
    if tag and tag.has_attr("data-id") and tag["data-id"]:
        return tag["data-id"].strip()
    # 2) div.item_data の data-product-id
    div_tag = soup.select_one("div.item_data")
    if div_tag and div_tag.has_attr("data-product-id") and div_tag["data-product-id"]:
        return div_tag["data-product-id"].strip()
    # 3) a.item_data_link の href から推定
    link_tag = soup.select_one("a.item_data_link")
    if link_tag and link_tag.has_attr("href"):
        href = link_tag["href"]
        if "/product/" in href:
            return href.split("/product/")[1].split("?")[0].strip()
    return ""


def parse_listing_li(li_html: str) -> List[str]:
    soup = BeautifulSoup(li_html, "html.parser")
    name_text = extract_text(soup, "span.goods_name")
    price_text = extract_text(soup, "p.selling_price span.figure")
    pack_code = extract_text(soup, "span.model_number_value")
    stock_text = extract_text(soup, "p.stock").replace("在庫数：", "")
    image_url = extract_image_url(soup)
    product_id = extract_product_id(soup)
    product_url = f"https://www.cardrush-pokemon.jp/product/detail/{product_id}" if product_id else ""
    return [name_text, price_text, pack_code, stock_text, image_url, product_id, product_url]


# =========================
# ユーティリティ
# =========================
def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: List[List[str]], mode: str = "new") -> None:
    """
    mode: new|append|overwrite
      - new: 既存ならエラー（上書きしない）
      - append: 追記（ヘッダーは無い場合のみ書く）
      - overwrite: 常に上書き（ヘッダー書く）
    """
    ensure_parent(path)
    header = ["商品名", "価格", "パック番号", "在庫数", "画像URL", "商品ID", "商品URL"]

    if mode == "new" and path.exists():
        raise FileExistsError(f"{path} は既に存在します。--csv-mode append または overwrite を使用してください。")

    write_header = True
    open_mode = "w"
    if mode == "append" and path.exists():
        write_header = False
        open_mode = "a"
    elif mode == "append":
        open_mode = "w"
    elif mode == "overwrite":
        open_mode = "w"

    with open(path, open_mode, newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(header)
        w.writerows(rows)


def discover_total_pages(driver: webdriver.Chrome, wait: WebDriverWait, first_url: str) -> int:
    """
    ページャから総ページ数を推定。なければ1。
    """
    driver.get(first_url)
    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.list_item_cell")))
    except TimeoutException:
        # 商品が0でもページャは出てこない可能性あり → 1扱い
        return 1

    # ページャ候補を探す
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    # よくあるパターン: .pagination 内の a の最大ページ番号
    page_nums: List[int] = []
    for a in soup.select("ul.pagination a"):
        try:
            page_nums.append(int(a.get_text(strip=True)))
        except Exception:
            continue

    return max(page_nums) if page_nums else 1


def rate_limit(last_time: List[float], rpm: Optional[int]) -> None:
    """
    1分あたりの最大実行回数（rpm）を擬似的に制限。
    """
    if not rpm:
        return
    min_interval = 60.0 / float(rpm)
    now = time.time()
    elapsed = now - last_time[0]
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    last_time[0] = time.time()


# =========================
# コア処理（★ リトライ時セッション再生成を組み込み）
# =========================
def scrape_pages(
    args: Args,
    driver: webdriver.Chrome,
    wait: WebDriverWait,
) -> Tuple[List[List[str]], webdriver.Chrome]:
    rows: List[List[str]] = []
    seen_ids: Set[str] = set()

    # 開始・終了ページの決定
    if args.mode == "group":
        assert args.group_id is not None, "mode=group では --group-id が必須です。"
        first_url = build_group_url(args.group_id, args.start_page)
    else:
        first_url = build_search_url(args.start_page, keyword=args.keyword)

    if args.all_pages:
        total_pages = discover_total_pages(driver, wait, first_url)
        start_page = 1
        end_page = total_pages
        print(f"🔎 総ページ数を自動検出: {total_pages} ページ")
    else:
        start_page = args.start_page
        end_page = args.end_page if args.end_page is not None else args.start_page

    # 進捗のざっくり表示用
    total_steps = max(1, end_page - start_page + 1)
    width = len(str(end_page))
    next_checkpoint_at = start_page + (args.checkpoint_every or 0)

    last_call = [0.0]  # rate limit管理

    for page in range(start_page, end_page + 1):
        # セッションリセット（一定ページごとにブラウザ再起動）
        if args.reset_session_every and (page - start_page) > 0 and (page - start_page) % args.reset_session_every == 0:
            print(f"🔄 セッションリセット（{args.reset_session_every}ページごと）...")
            try:
                driver.quit()
            except Exception:
                pass
            time.sleep(random.uniform(3.0, 6.0))  # 少し長めに休憩
            driver = make_driver(headful=args.headful)
            wait = WebDriverWait(driver, args.wait_sec)
            print("  → ブラウザ再起動完了")

        # レート制御
        rate_limit(last_call, args.rpm)

        # URL構築
        if args.mode == "group":
            url = build_group_url(args.group_id, page)
        else:
            url = build_search_url(page, keyword=args.keyword)

        # リトライ込みで取得（★失敗時はセッションを作り直す）
        last_err: Optional[Exception] = None
        for attempt in range(1, args.retry + 2):
            try:
                print(f"[{page:>{width}}/{end_page}] GET {url}  (try {attempt}/{args.retry + 1})")
                driver.get(url)
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.list_item_cell")))
                time.sleep(0.2)  # 軽い描画待ち

                items = driver.find_elements(By.CSS_SELECTOR, "li.list_item_cell")
                added_page = 0
                for it in items:
                    li_html = it.get_attribute("outerHTML")
                    row = parse_listing_li(li_html)

                    pid = row[5]
                    if pid and pid in seen_ids:
                        continue
                    if pid:
                        seen_ids.add(pid)

                    rows.append(row)
                    added_page += 1

                print(f"  → {added_page} 件")
                break  # 成功
            except Exception as e:
                last_err = e
                print(f"  ⚠️ エラー: {repr(e)}")

                # ★ ここが追加点：リトライ前にセッションをリセット
                try:
                    driver.quit()
                except Exception:
                    pass
                # 短いバックオフ＋新セッション
                backoff = 1.0 + 0.5 * attempt + random.uniform(0, 0.5)
                time.sleep(backoff)
                try:
                    driver = make_driver(headful=args.headful)
                    wait = WebDriverWait(driver, args.wait_sec)
                    print("  ↻ 新しいブラウザセッションで再試行します")
                except Exception as boot_e:
                    print(f"  ❌ セッション再生成に失敗: {repr(boot_e)}")
                    # さらに待って次のattemptへ（次のループでまた再生成を試みる）
                    time.sleep(1.5)

                if attempt > args.retry:
                    print(f"  ❌ ページ {page} をスキップ（最終エラー）: {repr(last_err)}")

        # ページ間の待機（ゆるランダム）
        time.sleep(args.delay + random.uniform(0, 0.4))

        # チェックポイント保存（★ 括弧で優先順位を明示）
        if args.checkpoint_every and (
            page == next_checkpoint_at or ((page - start_page + 1) % args.checkpoint_every == 0)
        ):
            try:
                print("💾 チェックポイント保存…")
                write_csv(args.output, rows, mode="overwrite")
                print("  → 保存完了")
            except Exception as e:
                print(f"  ⚠️ チェックポイント保存失敗: {e}")
            next_checkpoint_at = page + args.checkpoint_every

    return rows, driver


# =========================
# 引数処理
# =========================
def parse_args() -> Args:
    p = argparse.ArgumentParser(description="CardRush Pokemon listing scraper (usability enhanced)")
    p.add_argument("--mode", choices=["group", "search"], required=True, help="group or search")
    p.add_argument("--group-id", type=int, help="product-group/<ID> のID（mode=group時必須）")
    p.add_argument("--keyword", type=str, default="", help="検索キーワード（mode=search時有効）")

    p.add_argument("--start-page", type=int, default=1)
    p.add_argument("--end-page", type=int, help="未指定なら start-page のみ")
    p.add_argument("--all-pages", action="store_true", help="ページ数を自動検出して全ページを対象にする")

    p.add_argument("--output", type=Path, required=True, help="出力CSVファイル名")
    p.add_argument("--csv-mode", choices=["new", "append", "overwrite"], default="new",
                   help="CSVの出力モード: new(既存ならエラー)/append(追記)/overwrite(上書き)")

    p.add_argument("--headful", action="store_true", help="ヘッドレス無効化（ブラウザを表示）")
    p.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="ページ間の待機秒（ランダム微増あり）")
    p.add_argument("--retry", type=int, default=DEFAULT_RETRY, help="ページ取得の最大再試行回数")
    p.add_argument("--wait-sec", type=int, default=DEFAULT_WAIT_SEC, help="DOM待機の最大秒数")
    p.add_argument("--rpm", type=int, help="1分あたりの最大アクセス数（レート制御）")
    p.add_argument("--checkpoint-every", type=int, default=0,
                   help="指定ページごとに中間保存（0=しない）")
    p.add_argument("--reset-session-every", type=int, default=0,
                   help="指定ページごとにブラウザセッションをリセット（0=しない、推奨: 15-20）")

    a = p.parse_args()

    # バリデーション & 使い勝手向上
    if a.mode == "group" and a.group_id is None:
        p.error("mode=group では --group-id が必須です。")

    if a.all_pages and a.end_page is not None:
        print("ℹ️ --all-pages が指定されたため --end-page は無視します。", file=sys.stderr)

    return Args(
        mode=a.mode,
        group_id=a.group_id,
        keyword=a.keyword,
        start_page=a.start_page,
        end_page=a.end_page,
        all_pages=a.all_pages,
        output=a.output,
        csv_mode=a.csv_mode,
        headful=a.headful,
        delay=a.delay,
        retry=a.retry,
        wait_sec=a.wait_sec,
        rpm=a.rpm,
        checkpoint_every=a.checkpoint_every,
        reset_session_every=a.reset_session_every,
    )


# =========================
# エントリポイント（★ 最終ドライバを確実にquit）
# =========================
def main() -> int:
    args = parse_args()
    driver = make_driver(headful=args.headful)
    wait = WebDriverWait(driver, args.wait_sec)

    # 既存ファイルに追記/上書きの前準備
    if args.csv_mode == "overwrite" and args.output.exists():
        # 上書き開始前にヘッダで初期化
        write_csv(args.output, [], mode="overwrite")
    elif args.csv_mode == "new" and args.output.exists():
        print(f"❌ {args.output} は既に存在します。--csv-mode append/overwrite を検討してください。")
        try:
            driver.quit()
        except Exception:
            pass
        return 2
    elif args.csv_mode == "append" and not args.output.exists():
        # appendでも初回はヘッダ付きで作成
        write_csv(args.output, [], mode="append")

    try:
        rows, driver = scrape_pages(args, driver, wait)  # ★ 最新driverを受け取る
    finally:
        # ★ scrape_pages 内で新規生成したdriverがある可能性があるため、必ず最後の参照でquit
        try:
            driver.quit()
        except Exception:
            pass

    # 収集データを書き出し
    try:
        write_csv(args.output, rows, mode="append" if args.csv_mode == "append" else "overwrite")
    except FileExistsError:
        # csv_mode=new で既に存在していたケースはここには来ないはずだが二重防衛
        print(f"❌ {args.output} は既に存在します。--csv-mode append/overwrite にしてください。")
        return 2

    print(f"✅ 完了: {len(rows)} 件を {args.output} に保存しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())