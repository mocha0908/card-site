import argparse
import csv
import time
import random
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def make_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", type=str, required=True)
    parser.add_argument("--output", type=str, default="card_data.csv")
    parser.add_argument("--mode", type=str, default="overwrite")
    parser.add_argument("--end-page", type=int, default=5)
    args = parser.parse_args()

    print(f"🚀 販売データ取得開始: キーワード「{args.keyword}」")

    driver = make_driver()
    # 検索URL (100件表示)
    base_url = f"https://www.cardrush-pokemon.jp/product-list?keyword={args.keyword}&num=100&img=160"
    
    all_cards = []

    try:
        for page in range(1, args.end_page + 1):
            url = f"{base_url}&page={page}"
            print(f"📄 ページ {page} 取得中...")
            
            driver.get(url)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "item_box"))
                )
            except:
                print("⚠ 読み込みタイムアウト、または商品なし")
                break

            soup = BeautifulSoup(driver.page_source, "html.parser")
            items = soup.find_all("div", class_="item_box")
            
            if not items:
                print("✅ 商品がこれ以上ないため終了")
                break
                
            print(f"➡ {len(items)} 件取得")

            for item in items:
                name_tag = item.find("span", class_="goods_name")
                price_tag = item.find("span", class_="figure")
                img_tag = item.find("img")
                
                name = name_tag.text.strip() if name_tag else "-"
                price = price_tag.text.strip().replace(",", "") if price_tag else "0"
                
                img_url = ""
                if img_tag:
                    img_url = img_tag.get("data-src") or img_tag.get("src") or ""

                link_tag = item.find("a", class_="item_data_link")
                link_url = link_tag.get("href") if link_tag else ""
                if link_url.startswith("/"):
                    link_url = "https://www.cardrush-pokemon.jp" + link_url

                all_cards.append([name, price, img_url, link_url])
            
            time.sleep(random.uniform(2, 4))

    finally:
        if driver:
            driver.quit()

    # CSV保存処理
    write_mode = "w" if args.mode == "overwrite" else "a"
    file_exists = os.path.isfile(args.output)

    with open(args.output, write_mode, newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if args.mode == "overwrite" or not file_exists:
            writer.writerow(["商品名", "価格", "画像URL", "商品URL"])
        
        writer.writerows(all_cards)

    print(f"🎉 保存完了: {args.output} ({len(all_cards)}件)")

if __name__ == "__main__":
    main()
