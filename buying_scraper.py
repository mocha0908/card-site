from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import random

# === 設定 ===
csv_filename = "buying_data.csv"
base_url = "https://cardrush.media/pokemon/buying_prices"

def main():
    print("🚀 PCで買取データの取得を開始します...")
    
    header = [
        "カードID", "ocha_product_id", "カード名", "追加情報", "レアリティ", "型番", "タイプ",
        "パックコード", "レギュレーションブロック", "フォーマット", "買取価格", "人気カード",
        "カテゴリ", "表示カテゴリ", "最終更新日時", "レアリティ優先度", "パック名", "画像URL"
    ]

    try:
        with open(csv_filename, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(header)

            page = 1
            while True:
                target_url = f"{base_url}?page={page}"
                print(f"📄 ページ {page} にアクセス中... {target_url}")

                try:
                    # 日本の正規ユーザーになりすます設定
                    response = requests.get(
                        target_url, 
                        impersonate="chrome120", 
                        headers={
                            "Referer": "https://cardrush.media/",
                            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 403:
                        print("❌ 403 Forbidden（ブロックされました）。")
                        break
                    
                    if response.status_code != 200:
                        print(f"❌ ステータスコード異常: {response.status_code}")
                        break

                    soup = BeautifulSoup(response.text, "html.parser")
                    script_tag = soup.find("script", id="__NEXT_DATA__")

                    if not script_tag:
                        print("❌ データタグが見つかりません。")
                        break

                    data = json.loads(script_tag.string)
                    buying_prices = (
                        data.get("props", {})
                        .get("pageProps", {})
                        .get("buyingPrices", [])
                    )

                    if not buying_prices:
                        print("✅ データが空でした。終了します。")
                        break

                    print(f"➡ {len(buying_prices)} 件取得")

                    for card in buying_prices:
                        img_src = card.get("ocha_product", {}).get("image_source", "")
                        writer.writerow([
                            card.get("id", ""),
                            card.get("pokemon_ocha_product_id", ""),
                            card.get("name", ""),
                            card.get("extra_difference", ""),
                            card.get("rarity", ""),
                            card.get("model_number", ""),
                            card.get("element", ""),
                            card.get("pack_code", ""),
                            card.get("regulation_block", ""),
                            card.get("regulation", ""),
                            card.get("amount", ""),
                            card.get("is_hot", ""),
                            card.get("product_cvategory", ""),
                            card.get("display_category", ""),
                            card.get("updated_at", ""),
                            card.get("rarity_priority", ""),
                            card.get("pack_name", ""),
                            img_src,
                        ])

                    page += 1
                    time.sleep(random.uniform(2, 5))

                except Exception as e:
                    print(f"💥 エラー: {e}")
                    break
    except Exception as e:
        print(f"ファイルエラー: {e}")

    print(f"🎉 処理終了: {csv_filename}")

if __name__ == "__main__":
    main()