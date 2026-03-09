from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import random
import sys
import os
import shutil
from datetime import datetime

# ==========================================
# 設定エリア
# ==========================================
CSV_FILENAME = "buying_data.csv"
BASE_URL = "https://cardrush.media/pokemon/buying_prices"
MAX_RETRIES = 5

# Googleドライブの同期先（あなたの環境に合わせて調整済み）
GOOGLE_DRIVE_PATH = "/Users/tcrairai_sub/Library/CloudStorage/GoogleDrive-rairai.tcg@gmail.com/My Drive/buying_data.csv"
# 万が一上記が英語名でエラーになる場合用の日本語パス
GOOGLE_DRIVE_PATH_JP = "/Users/tcrairai_sub/Library/CloudStorage/GoogleDrive-rairai.tcg@gmail.com/マイドライブ/buying_data.csv"

# ★活動時間設定 (7時〜25時)
ACTIVE_HOUR_START = 7
ACTIVE_HOUR_END = 25 

# ==========================================
# ユーティリティ関数
# ==========================================

def is_sleeping_time():
    current_hour = datetime.now().hour
    if ACTIVE_HOUR_START < ACTIVE_HOUR_END:
        return not (ACTIVE_HOUR_START <= current_hour < ACTIVE_HOUR_END)
    else:
        return not (ACTIVE_HOUR_START <= current_hour or current_hour < ACTIVE_HOUR_END - 24)

def get_header():
    return [
        "カードID", "ocha_product_id", "カード名", "追加情報", "レアリティ", "型番", "タイプ",
        "パックコード", "レギュレーションブロック", "フォーマット", "買取価格", "人気カード",
        "カテゴリ", "表示カテゴリ", "最終更新日時", "レアリティ優先度", "パック名", "画像URL"
    ]

def init_csv():
    try:
        with open(CSV_FILENAME, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(get_header())
        print(f"📁 ファイルをリセットしました: {CSV_FILENAME}")
    except Exception as e:
        print(f"❌ ファイル初期化エラー: {e}")
        sys.exit(1)

def append_to_csv(rows):
    try:
        with open(CSV_FILENAME, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    except Exception as e:
        print(f"❌ 書き込みエラー: {e}")

def create_session():
    # 指紋をバラつかせる
    impersonate_ver = random.choice(["chrome124", "chrome120", "safari15_5", "edge101"])
    session = requests.Session(impersonate=impersonate_ver)
    session.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Referer": "https://cardrush.media/",
        "Sec-Ch-Ua-Mobile": "?0",
        "Upgrade-Insecure-Requests": "1",
    })
    return session

def random_sleep(min_sec, max_sec):
    # 10%の確率で「長い休憩」を入れてAI検知を回避
    if random.random() < 0.1:
        long_wait = random.uniform(15, 30)
        print(f"\n☕️ 相手サーバーを休ませるため一時停止中... ({long_wait:.1f}秒)")
        time.sleep(long_wait)
    else:
        mu = (min_sec + max_sec) / 2
        sigma = (max_sec - min_sec) / 4
        sleep_time = random.gauss(mu, sigma)
        sleep_time = max(min_sec, min(sleep_time, max_sec))
        time.sleep(sleep_time)

def sync_to_google_drive():
    """完成したCSVをGoogleドライブのパスにコピーする"""
    print("\n☁️ Googleドライブへ同期を開始します...")
    try:
        if os.path.exists(os.path.dirname(GOOGLE_DRIVE_PATH)):
            shutil.copy(CSV_FILENAME, GOOGLE_DRIVE_PATH)
            print(f"✅ 同期成功 (My Drive)")
        elif os.path.exists(os.path.dirname(GOOGLE_DRIVE_PATH_JP)):
            shutil.copy(CSV_FILENAME, GOOGLE_DRIVE_PATH_JP)
            print(f"✅ 同期成功 (マイドライブ)")
        else:
            print("⚠️ Googleドライブのフォルダが見つかりませんでした。パスを確認してください。")
    except Exception as e:
        print(f"❌ 同期エラー: {e}")

# ==========================================
# メイン処理
# ==========================================
def main():
    if is_sleeping_time():
        print(f"💤 活動時間外です。終了します。")
        sys.exit(0)

    print(f"🚀 買取データ取得開始: {datetime.now().strftime('%H:%M:%S')}")
    init_csv()

    session = create_session()
    page = 1
    current_referer = "https://cardrush.media/"
    
    # 20ページ前後でセッション（指紋）を強制リセット
    reset_countdown = random.randint(15, 25)

    while True:
        target_url = f"{BASE_URL}?page={page}"
        
        reset_countdown -= 1
        if reset_countdown <= 0:
            print("\n🔄 セッションをリフレッシュして指紋を変更します...")
            session.close()
            time.sleep(random.randint(5, 10))
            session = create_session()
            reset_countdown = random.randint(15, 25)

        page_data = []
        success = False

        for attempt in range(MAX_RETRIES):
            try:
                session.headers.update({"Referer": current_referer})
                random_sleep(4, 7) # 待機時間を少し長めに修正
                
                print(f"📄 [{page}] 取得中... (試行 {attempt+1}/{MAX_RETRIES})", end="\r")
                response = session.get(target_url, timeout=60)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    script_tag = soup.find("script", id="__NEXT_DATA__")

                    if not script_tag: raise ValueError("No Data Tag")

                    data_json = json.loads(script_tag.string)
                    buying_prices = data_json.get("props", {}).get("pageProps", {}).get("buyingPrices", [])

                    if not buying_prices:
                        if page < 100: # まだページがあるはずなのに空
                            print(f"\n🛡️ ソフトブロックの可能性。少し長く待ちます。")
                            raise ValueError("Empty Data Received")
                        else:
                            print("\n✅ 全ページ取得完了しました。")
                            sync_to_google_drive()
                            sys.exit(0)

                    for card in buying_prices:
                        img_src = card.get("ocha_product", {}).get("image_source", "")
                        row = [
                            card.get("id", ""), card.get("pokemon_ocha_product_id", ""),
                            card.get("name", ""), card.get("extra_difference", ""),
                            card.get("rarity", ""), card.get("model_number", ""),
                            card.get("element", ""), card.get("pack_code", ""),
                            card.get("regulation_block", ""), card.get("regulation", ""),
                            card.get("amount", ""), card.get("is_hot", ""),
                            card.get("product_cvategory", ""), card.get("display_category", ""),
                            card.get("updated_at", ""), card.get("rarity_priority", ""),
                            card.get("pack_name", ""), img_src
                        ]
                        page_data.append(row)
                    
                    success = True
                    print(f"📄 [{page}] 成功: {len(page_data)}件取得        ")
                    break

                elif response.status_code in [403, 429, 503]:
                    # 接続拒絶時は、リトライ回数に応じて待ち時間を長くする
                    wait_time = (attempt + 1) * random.randint(60, 120)
                    print(f"\n🛑 制限検知 ({response.status_code}) - {wait_time}秒 待機して回避します...")
                    session.close()
                    time.sleep(wait_time)
                    session = create_session()
                else:
                    time.sleep(10)

            except Exception as e:
                wait_time = (attempt + 1) * 30
                print(f"\n❌ 通信エラー: {e} - {wait_time}秒後に再試行します")
                session.close()
                time.sleep(wait_time)
                session = create_session()

        if not success:
            print(f"\n💀 ページ {page} で断念しました。")
            sync_to_google_drive() # 失敗してもそこまでの分を同期
            sys.exit(1)

        if page_data:
            append_to_csv(page_data)
        
        current_referer = target_url
        page += 1

if __name__ == "__main__":
    main()
