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

# =========================
# 設定系
# =========================
DEFAULT_WAIT_SEC = 15
DEFAULT_RETRY = 2
DEFAULT_DELAY = 1.0
# シンタックスエラー回避のため1行で記述
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

@dataclass
class Args:
    mode: str
    group_id: Optional[int]
    keyword: str
    start_page: int
    end_page: Optional[int]
    all_pages: bool
    output: Path
    csv_mode: str
    headful: bool
    delay: float
    retry: int
    wait_sec: int
    rpm: Optional[int]
    checkpoint_every: int
    reset_session_every: int

# =========================
# ドライバ生成
# =========================
def find_chromedriver_executable(base_path: str) -> str:
    base_dir = Path(base_path).parent
    possible_files = ["chromedriver", "chromedriver-mac-arm64", "chromedriver-mac-x64", "chromedriver.exe"]
    for filename in possible_files:
        candidate = base_dir / filename
        if candidate.exists() and candidate.is_file():
            if platform.system() != "Windows":
                st = candidate.stat()
                if st.st_mode & stat.S_IXUSR:
                    return str(candidate)
            else:
                if filename.endswith(".exe"):
                    return str(candidate)
    return base_path

def make_driver(headful: bool) -> webdriver.Chrome:
    options = Options()
    if not headful and not os.environ.get("HEADFUL"):
        options.add_argument("--headless=new")
    
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,2000")
    options.add_argument("--lang=ja-JP")
    options.add_argument(f"--user-agent={USER_AGENT}")
    
    # ロボット検知回避
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    driver_path = None
    local_driver = Path(__file__).parent / "chromedriver"
    if local_driver.exists() and local_driver.is_file():
        st = local_driver.stat()
        if platform.system() != "Windows" and not (st.st_mode & stat.S_IXUSR):
            local_driver.chmod(st.st_mode | stat.S_IXUSR)
        driver_path = str(local_driver)

    if not driver_path:
        try:
            driver_path = ChromeDriverManager().install()
            if platform.system() == "Darwin":
                driver_path = find_chromedriver_executable(driver_path)
        except Exception:
            raise RuntimeError("ChromeDriverのインストールに失敗しました")

    return webdriver.Chrome(service=Service(driver_path), options=options)

# =========================
# URLビルダ
# =========================
def build_group_url(group_id: int, page: int) -> str:
    # num=100 を付与して1ページあたりの取得数を最大化
    base = f"https://www.cardrush-pokemon.jp/product-group/{group_id}"
    return f"{base}?page={page}&num=100&img=160"

def build_search_url(page: int, keyword: str, num: int = 100, img: int = 160) -> str:
    base = "https://www.cardrush-pokemon.jp/product-list"
    query = {"keyword": keyword, "Submit": "検索", "num": str(num), "img": str(img), "page": page}
    return f"{base}?{urlencode(query)}"

# =========================
# パース処理 (Correct Selectors)
# =========================
def extract_text(soup: BeautifulSoup, selector: str, default: str = "") -> str:
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else default

def extract_image_url(soup: BeautifulSoup) -> str:
    img = soup.select_one("img")
    if not img:
        return ""
    # 遅延読み込み対応: data-x2 > data-src > src
    return img.get("data-x2") or img.get("data-src") or img.get("src", "") or ""

def extract_product_id(soup: BeautifulSoup) -> str:
    # URLからIDを抽出するのが最も確実
    link_tag = soup.select_one("a")
    if link_tag and link_tag.has_attr("href"):
        href = link_tag["href"]
        if "/product/" in href:
            try:
                return href.split("/product/")[1].split("?")[0].strip()
            except:
                pass
    return ""

def parse_listing_li(li_html: str) -> List[str]:
    # リスト構造 li.list_item_cell に対応
    soup = BeautifulSoup(li_html, "html.parser")
    
    name_text = extract_text(soup, "span.goods_name")
    price_text = extract_text(soup, "span.figure").replace(",", "")
    # stockは "在庫数 5点" のような形式
    stock_raw = extract_text(soup, "p.stock")
    stock_text = stock_raw.replace("在庫数", "").replace("点", "").replace("枚", "").strip()
    
    image_url = extract_image_url(soup)
    product_id = extract_product_id(soup)
    product_url = f"https://www.cardrush-pokemon.jp/product/{product_id}" if product_id else ""
    
    return [name_text, price_text, stock_text, image_url, product_url]

# =========================
# ファイル処理
# =========================
def write_csv(path: Path, rows: List[List[str]], mode: str = "new") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["商品名", "価格", "在庫数", "画像URL", "商品URL"]

    write_header = True
    open_mode = "w"
    
    if mode == "append":
        if path.exists():
            write_header = False
            open_mode = "a"
    elif mode == "overwrite":
        open_mode = "w"
    
    with open(path, open_mode, newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(header)
        w.writerows(rows)

# =========================
# スクレイピングコア
# =========================
def discover_total_pages(driver: webdriver.Chrome, wait: WebDriverWait, first_url: str) -> int:
    driver.get(first_url)
    try:
        # 商品リストが出るまで待つ (正しいセレクタ)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "list_item_cell")))
    except TimeoutException:
        # 商品が無い、または読み込み失敗
        return 1

    soup = BeautifulSoup(driver.page_source, "html.parser")
    # ページネーションから最大ページを取得
    # 例: [1] [2] ... [46] [次へ]
    # カードラッシュの構造依存
    page_links = soup.select("div.pager a")
    max_page = 1
    for link in page_links:
        txt = link.get_text(strip=True)
        if txt.isdigit():
            p = int(txt)
            if p > max_page:
                max_page = p
    return max_page

def scrape_pages(args: Args, driver: webdriver.Chrome, wait: WebDriverWait) -> Tuple[List[List[str]], webdriver.Chrome]:
    rows: List[List[str]] = []
    
    if args.mode == "group":
        first_url = build_group_url(args.group_id, args.start_page)
    else:
        first_url = build_search_url(args.start_page, keyword=args.keyword)

    if args.all_pages:
        print("🔎 総ページ数を確認中...")
        total_pages = discover_total_pages(driver, wait, first_url)
        start_page = 1
        end_page = total_pages
        print(f"🔎 総ページ数: {total_pages}")
    else:
        start_page = args.start_page
        end_page = args.end_page if args.end_page else args.start_page

    for page in range(start_page, end_page + 1):
        # セッションリセット
        if args.reset_session_every and (page - start_page) > 0 and (page - start_page) % args.reset_session_every == 0:
            print("🔄 ブラウザ再起動中...")
            driver.quit()
            time.sleep(3)
            driver = make_driver(headful=args.headful)
            wait = WebDriverWait(driver, args.wait_sec)

        # URL決定
        if args.mode == "group":
            url = build_group_url(args.group_id, page)
        else:
            url = build_search_url(page, keyword=args.keyword)
        
        # 取得トライ
        for attempt in range(args.retry + 1):
            try:
                print(f"[{page}/{end_page}] 取得中: {url}")
                driver.get(url)
                
                # ★修正: 正しいクラス名 list_item_cell を待機
                wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "list_item_cell")))
                
                # 画像読み込み誘発
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)

                items = driver.find_elements(By.CLASS_NAME, "list_item_cell")
                if not items:
                     # 念のためBeautifulSoupでも確認
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    if not soup.select("li.list_item_cell"):
                        print("  ⚠ 商品が見つかりません (0件)")
                        break

                current_rows = []
                for it in items:
                    current_rows.append(parse_listing_li(it.get_attribute("outerHTML")))
                
                rows.extend(current_rows)
                print(f"  → {len(current_rows)} 件")
                break # 成功

            except Exception as e:
                print(f"  ⚠ エラー (try {attempt+1}): {e}")
                time.sleep(3)
                if attempt == args.retry:
                    print("  ❌ このページをスキップします")

        time.sleep(args.delay + random.uniform(0, 1.0))
        
        # チェックポイント
        if args.checkpoint_every and page % args.checkpoint_every == 0:
            write_csv(args.output, rows, mode="overwrite")
            print(f"💾 中間保存完了 ({len(rows)}件)")

    return rows, driver

# =========================
# メイン
# =========================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["group", "search"], required=True)
    parser.add_argument("--group-id", type=int)
    parser.add_argument("--keyword", type=str, default="")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int)
    parser.add_argument("--all-pages", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv-mode", choices=["new", "append", "overwrite"], default="new")
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--retry", type=int, default=DEFAULT_RETRY)
    parser.add_argument("--wait-sec", type=int, default=DEFAULT_WAIT_SEC)
    parser.add_argument("--rpm", type=int)
    parser.add_argument("--checkpoint-every", type=int, default=0)
    parser.add_argument("--reset-session-every", type=int, default=0)

    args_parsed = parser.parse_args()
    
    # バリデーション
    if args_parsed.mode == "group" and not args_parsed.group_id:
        parser.error("--group-id is required for group mode")

    args = Args(**vars(args_parsed))
    
    driver = make_driver(headful=args.headful)
    wait = WebDriverWait(driver, args.wait_sec)

    try:
        # ヘッダー初期化(overwrite/newの場合)
        if args.csv_mode in ["overwrite", "new"]:
            if args.csv_mode == "new" and args.output.exists():
                print(f"❌ ファイルが存在します: {args.output}")
                return
            write_csv(args.output, [], mode=args.csv_mode)

        rows, driver = scrape_pages(args, driver, wait)
        
        # 最終保存 (appendなら追記)
        save_mode = "append" if args.csv_mode == "append" else "overwrite"
        write_csv(args.output, rows, mode=save_mode)
        print(f"🎉 全完了: {len(rows)} 件を保存しました")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
