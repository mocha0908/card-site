import os
import time
import random
import argparse
import pandas as pd
import subprocess
import re
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    
    # 💡 【爆速化1】せっかちモード：画像の読み込みなどを待たずにHTMLが出たら完了とする
    options.page_load_strategy = 'eager'
    
    # 💡 【爆速化2】画像を一切読み込まない設定（通信量激減・超高速化）
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    profile_path = os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f'--user-data-dir={profile_path}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1200,800')
    
    driver = uc.Chrome(options=options, version_main=get_mac_chrome_version())
    
    # 💡 読み込み待ちの限界時間を60秒から30秒に短縮
    driver.set_page_load_timeout(30) 
    
    return driver

def parse_listing_li(html):
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. 商品名
    name_el = soup.select_one("span.goods_name")
    name = name_el.get_text(strip=True) if name_el else "不明"
    
    # 2. 価格
    price_el = soup.select_one("span.figure")
    price = price_el.get_text(strip=True).replace(",", "").replace("円", "") if price_el else "0"
    
    # 3. 在庫数の完全判定（「×」対応 ＆ 数字抽出）
    html_lower = html.lower()
    
    if any(word in html_lower for word in ["売り切れ", "sold", "在庫なし", "在庫切れ", "soldout"]):
        stock = 0
    else:
        stock_el = soup.select_one("p.stock")
        if stock_el:
            stock_text = stock_el.get_text(strip=True)
            if "×" in stock_text or "✖" in stock_text:
                stock = 0
            else:
                match = re.search(r'(\d+)', stock_text)
                if match:
                    stock = int(match.group(1))
                else:
                    stock = 1 
        else:
            if "×" in html_lower or "✖" in html_lower:
                stock = 0
            else:
                stock = 1
            
        # 4. 画像URL
    img = soup.select_one("img")
    image_url = img.get("data-x2") or img.get("data-src") or img.get("src", "") if img else ""
    
    # 5. 商品URL
    link = soup.select_one("a")
    href = link.get("href", "") if link else ""
    p_url = f"https://www.cardrush-pokemon.jp{href}" if href.startswith("/") else href
    
    return [name, price, stock, image_url, p_url]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="全商品を取得モード")
    parser.add_argument("--keyword", type=str)     
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()

    if args.all:
        print("\n🔥 [MODE] 全商品一括取得・爆速モード起動")
        base_url = "https://www.cardrush-pokemon.jp/product-list?keyword=" 
    else:
        base_url = f"https://www.cardrush-pokemon.jp/product-list?keyword={args.keyword}"

    page_num = 1
    last_page_content = "" 
    
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
                
                # 💡 要素出現待ちも45秒から30秒へ短縮
                WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "list_item_cell")))
                
                items = driver.find_elements(By.CLASS_NAME, "list_item_cell")
                current_page_content = "".join([it.get_attribute("outerHTML") for it in items])

                if not items:
                    print(f"  ✅ Page {page_num:03}: データなし。終了。          ")
                    break

                if current_page_content == last_page_content:
                    print(f"  🏁 Page {page_num:03}: ループ検知（最後のページを越えました）。完了！")
                    break
                
                last_page_content = current_page_content 

                page_data = []
                for it in items:
                    page_data.append(parse_listing_li(it.get_attribute("outerHTML")))
                
                df = pd.DataFrame(page_data, columns=["商品名", "価格", "在庫数", "画像URL", "商品URL"])
                df.to_csv(args.output, mode='a', header=False, index=False, encoding="utf-8-sig")
                
                print(f"  🔹 Page {page_num:03}: +{len(items):3}件 (保存完了) [OK]")
                
                if len(items) < 100:
                    print(f"  🏁 最終ページ到達。")
                    break
                
                page_num += 1
                
                # 💡 【爆速化3】次のページへ行く前の待機時間を半分以下に短縮
                time.sleep(random.uniform(1.5, 3))

            except Exception as e:
                print(f"\n  ⚠️  Page {page_num} でタイムアウト発生。")
                print(f"  🛠  ブラウザを再起動して {page_num}ページ目 から再開します...")
                try: driver.quit()
                except: pass
                
                # 💡 エラー時のリフレッシュ待機も15秒から5秒へ短縮
                time.sleep(5)
                driver = setup_driver()
                continue

    finally:
        try: driver.quit()
        except: pass
        print(f"\n🎉 全工程終了！")

if __name__ == "__main__":
    main()
