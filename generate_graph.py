import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os

def main():
    csv_file = "card_data.csv"
    history_file = "average_history.csv"
    graph_file = "average_graph.png"
    
    # 1. 今日のデータを読み込んで平均値を計算
    try:
        df = pd.read_csv(csv_file)
        # 価格を確実に数値（数字）に変換
        df['価格'] = pd.to_numeric(df['価格'], errors='coerce').fillna(0)
        # 0円（売り切れやエラー）を除外して平均を計算
        valid_prices = df[df['価格'] > 0]['価格']
        
        if len(valid_prices) == 0:
            print("有効な価格データがありません。")
            return
            
        avg_price = valid_prices.mean()
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        print(f"📊 今日の平均価格: {avg_price:.2f}円 (対象: {len(valid_prices)}件)")
        
    except Exception as e:
        print(f"エラー（読み込み）: {e}")
        return

    # 2. 履歴データ（average_history.csv）を更新
    try:
        if os.path.exists(history_file):
            hist_df = pd.read_csv(history_file)
        else:
            hist_df = pd.DataFrame(columns=["日付", "平均価格"])

        # 今日のデータが既にアレば削除（1日に複数回実行した時の上書き用）
        hist_df = hist_df[hist_df['日付'] != today_str]
        
        # 今日のデータを追加
        new_row = pd.DataFrame({"日付": [today_str], "平均価格": [avg_price]})
        hist_df = pd.concat([hist_df, new_row], ignore_index=True)
        
        # 日付順に並び替えて保存
        hist_df = hist_df.sort_values('日付')
        hist_df.to_csv(history_file, index=False, encoding="utf-8-sig")
        
    except Exception as e:
        print(f"エラー（履歴保存）: {e}")
        return

    # 3. 折れ線グラフの画像を作成
    try:
        # Macの日本語フォント設定（文字化け対策）
        plt.rcParams['font.family'] = ['Hiragino Sans', 'AppleGothic', 'sans-serif']
        
        # 日付型に変換
        hist_df['日付'] = pd.to_datetime(hist_df['日付'])
        
        # グラフの描画設定
        plt.figure(figsize=(10, 6))
        plt.plot(hist_df['日付'], hist_df['平均価格'], marker='o', linestyle='-', color='#FF5A5F', linewidth=2)
        
        plt.title('カードラッシュ 全商品平均価格の推移', fontsize=16, fontweight='bold')
        plt.xlabel('日付', fontsize=12)
        plt.ylabel('平均価格 (円)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # X軸の日付を見やすくする (例: 02/16)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 画像として保存
        plt.savefig(graph_file, dpi=150)
        print(f"📈 グラフ画像を更新しました: {graph_file}")
        
    except Exception as e:
        print(f"エラー（グラフ作成）: {e}")

if __name__ == "__main__":
    main()