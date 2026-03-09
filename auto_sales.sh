#!/bin/bash

# 設定
PYTHON_CMD="/usr/bin/python3"
FINAL_FILE="card_data.csv"
LOG_FILE="run_time.log"

while ! ping -c 1 8.8.8.8 &> /dev/null; do sleep 30; done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 [Full Scan] 全商品一括取得を開始します"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "▶︎ スタート: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"

# 1. メイン処理（スクレイピング）
$PYTHON_CMD scraper.py --all --output "$FINAL_FILE"

# 💡 2. 【追加】グラフの生成
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 平均価格の計算とグラフ作成中..."
$PYTHON_CMD generate_graph.py

echo "■ ゴール　: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"

# 3. GitHubへ送信
if [ -f "$FINAL_FILE" ]; then
    echo "📦 GitHubへ送信中..."
    git add "$FINAL_FILE"
    git add "$LOG_FILE"
    # 💡 【追加】履歴CSVとグラフ画像も送信する
    git add "average_history.csv"
    git add "average_graph.png"
    
    git commit -m "🤖 Full Update: $(date '+%Y-%m-%d %H:%M')"
    git push origin main
    echo "✅ 送信完了"
else
    echo "❌ ファイルが生成されていません"
ficp "card_data.csv" "/Users/tcrairai_sub/Library/CloudStorage/GoogleDrive-rairai.tcg@gmail.com/My Drive/" 2>/dev/null || cp "card_data.csv" "/Users/tcrairai_sub/Library/CloudStorage/GoogleDrive-rairai.tcg@gmail.com/マイドライブ/" 2>/dev/null
