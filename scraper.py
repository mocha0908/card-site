import os
import time
import random
import argparse
import pandas as pd
import subprocess
import re
import shutil
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# 設定エリア
# ==========================================
# Googleドライブの同期先パス
GOOGLE_DRIVE_PATH = "/Users/tcrairai_sub/Library/CloudStorage/GoogleDrive-rairai.tcg@gmail.com/My Drive/sales_data.csv"

def sync_to_google_drive(local_path):
    """保存したCSVをGoogleドライブにコピーする"""
    print("\n☁️ Googleドライブへ同期を開始します...")
    try:
        drive_dir = os.path.dirname(GOOGLE_DRIVE_PATH)
        if os.path.exists(drive_dir):
            shutil.copy(local_path, GOOGLE_DRIVE_PATH)
            print(f"✅ Googleドライブ同期成功！")
        else:
            print(f"⚠️ ドライブのパスが見つかりません: {drive_dir}")
    except Exception as e:
        print(f"❌ 同期エラー: {e}")

# ==========================================
# ユーティリティ・スクレイピング関数
# ==========================================
def get_mac_chrome_version():
    try:
        process = subprocess.Popen(
            ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = process.communicate()
        version_str = out.decode('utf-8').strip()
        match = re.search(r'Google Chrome (\d+)', version_str)
        return int(match.group(1)) if match else None
    except: return None

def setup_driver():
    options = uc.ChromeOptions()
    options.page_load_strategy = 'eager'
    
    # 画像を読み込まない設定（高速化）
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    profile_path = os.path.join(os.getcwd(), "chrome_profile_sales")
    options.add_argument(f'--user-data-dir={profile_path}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1200,800')
    
    driver = uc.Chrome(options=options, version_main=get_mac_chrome_version())
    driver.set_page_load_timeout(30) 
    return driver

def parse_listing_li(html):
    """
    1つの商品セル(li/div)から情報を抽出する。
    「×」表示やSOLD OUT画像を検知して在庫を0にする。
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # --- 商品名 ---
    name_el = soup.select_one("span.goods_name")
    name = name_el.get_text(strip=True) if name_el else "不明"
    
    # --- 価格 ---
    price_el = soup.select_one("span.figure")
    price = price_el.get_text(strip=True).replace(",", "").replace("円", "") if price_el else "0"
    
    # --- 在庫判定（強化版） ---
    stock = 1  # デフォルトは在庫あり
    html_lower = html.lower()
    # テキスト全体を取得（タグ間の結合を防ぐためスペース区切り）
    full_text = soup.get_text(separator=' ', strip=True).upper()
    
    # 判定キーワード（全角・半角の×を含む）
    out_of_stock_keywords = ["売り切れ", "SOLD OUT", "在庫切れ", "在庫なし", "×", "✖", "✕", "SOLD_OUT"]

    # 1. テキストベースの判定
    if any(word in full_text for word in out_of_stock_keywords):
        stock = 0
    
    # 2. 画像のALT属性や特定のクラス名があるか確認
    img_tag = soup.select_one("img")
    img_alt = img_tag.get("alt", "").upper() if img_tag else ""
    if any(word in img_alt for word in out_of_stock_keywords):
        stock = 0
    
    # 3. カードラッシュ特有の売り切れクラスや構造のチェック
    if "is-soldout" in html_lower or "soldout" in html_lower or soup.select_one(".soldout_icon"):
        stock = 0

    # 4. 「在庫：×」などの具体的な要素がある場合
    stock_el = soup.select_one("p.stock")
    if stock_el:
        stock_text = stock_el.get_text(strip=True)
        if any(x in stock_text for x in ["×", "✖", "✕", "なし"]):
            stock = 0
        else:
            match = re.search(r'(\d+)', stock_text)
            if match:
                stock = int(match.group(1))

    # --- 画像URL ---
    image_url = ""
    if img_tag:
        image_url = img_tag.get("data-x2") or img_tag.get("data-src") or img_tag.get("src", "")
    
    # --- 商品URL ---
    link = soup.select_one("a")
    href = link.get("href", "") if link else ""
    p_url = f"https://www.cardrush-pokemon.jp{href}" if href.startswith("/") else href
    
    return [name, price, stock, image_url, p_url]

# ==========================================
# メイン処理
# ==========================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="全商品を取得モード")
    parser.add_argument("--keyword", type=str)     
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()

    if args.all:
        print("\n🔥 [MODE] 全商品一括取得（販売データ）")
        base_url = "https://www.cardrush-pokemon.jp/product-list?keyword=" 
    else:
        print(f"\n🔍 [MODE] キーワード検索: {args.keyword}")
        base_url = f"https://www.cardrush-pokemon.jp/product-list?keyword={args.keyword}"

    page_num = 1
    last_page_content = "" 
    
    # 出力ファイルの初期化
    if os.path.exists(args.output):
        os.remove(args.output)
    dummy_df = pd.DataFrame(columns=["商品名", "価格", "在庫数", "画像URL", "商品URL"])
    dummy_df.to_csv(args.output, index=False, encoding="utf-8-sig")

    driver = setup_driver()

    try:
        while True:
            sep = "&" if "?" in base_url else "?"
            url = f"{base_url}{sep}num=100&page={page_num}"
            
            try:
                print(f"  ⏳ Page {page_num:03} 読込中...", end="\r")
                driver.get(url)
                
                # 要素が表示されるまで待機
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "list_item_cell"))
                )
                
                # 商品リストを取得
                items = driver.find_elements(By.CLASS_NAME, "list_item_cell")
                current_page_content = "".join([it.get_attribute("outerHTML") for it in items[:3]]) # 軽量化のため一部で比較

                if not items or current_page_content == last_page_content:
                    print(f"  ✅ Page {page_num:03}: 終了検知（これ以上のページはありません）。")
                    break
                
                last_page_content = current_page_content 

                page_data = []
                for it in items:
                    # 各アイテムのHTMLを解析
                    page_data.append(parse_listing_li(it.get_attribute("outerHTML")))
                
                # 取得したデータをCSVに追記保存
                df = pd.DataFrame(page_data, columns=["商品名", "価格", "在庫数", "画像URL", "商品URL"])
                df.to_csv(args.output, mode='a', header=False, index=False, encoding="utf-8-sig")
                
                print(f"  🔹 Page {page_num:03}: +{len(items):3}件保存 [OK]")
                
                if len(items) < 100: 
                    print("  🏁 最終ページに到達しました。")
                    break
                    
                page_num += 1
                time.sleep(random.uniform(1.5, 3)) # サーバー負荷軽減

            except Exception as e:
                print(f"\n  ⚠️ Page {page_num} でエラーまたはタイムアウト。リトライします...")
                time.sleep(5)
                driver.quit()
                driver = setup_driver()
                continue

    finally:
        try: driver.quit()
        except: pass
        
        # 保存完了後にGoogleドライブへ同期
        sync_to_google_drive(args.output)
        print(f"\n🎉 すべての工程が終了しました。")

if __name__ == "__main__":
    main()
