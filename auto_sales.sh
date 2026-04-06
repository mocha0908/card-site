#!/bin/bash

# ==========================================
# 設定
# ==========================================
PYTHON_CMD="/usr/bin/python3"
FINAL_FILE="card_data.csv"
LOG_FILE="run_time.log"

# Google Driveのベースパス
GDRIVE_BASE="/Users/tcrairai_sub/Library/CloudStorage/GoogleDrive-rairai.tcg@gmail.com"

# ==========================================
# ネットワーク接続待機（最大5回）
# ==========================================
RETRY_COUNT=0
while ! ping -c 1 8.8.8.8 &> /dev/null; do
    if [ $RETRY_COUNT -ge 5 ]; then
        echo "❌ ネットワークエラー: 終了します"
        exit 1
    fi
    echo "🌐 接続待機中..."
    sleep 30
    ((RETRY_COUNT++))
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 [Full Scan] 開始: $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶︎ スタート: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"

# 1. スクレイピング実行
$PYTHON_CMD scraper.py --all --output "$FINAL_FILE"

# 2. グラフ生成
if [ -f "$FINAL_FILE" ]; then
    echo "📊 グラフ作成中..."
    $PYTHON_CMD generate_graph.py
else
    echo "⚠️ CSVが生成されなかったため、グラフ作成をスキップします"
fi

echo "■ ゴール: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"

# 3. GitHubへ送信
if [ -f "$FINAL_FILE" ]; then
    echo "📦 GitHubへ送信中..."
    # .gitignore を無視して強制的に追加
    git add -f "$FINAL_FILE"
    git add "$LOG_FILE" "average_history.csv" "average_graph.png"
    
    git commit -m "🤖 Full Update: $(date '+%Y-%m-%d %H:%M')"
    git push origin main
    echo "✅ GitHub送信完了"
else
    echo "❌ ファイルが存在しません。GitHub送信を中止します。"
fi

# 4. Google Driveへバックアップ
echo "📁 Google Driveへバックアップ中..."

# 同期フォルダ（マイドライブ または My Drive）を自動特定
TARGET_DIR=""
if [ -d "$GDRIVE_BASE/マイドライブ" ]; then
    TARGET_DIR="$GDRIVE_BASE/マイドライブ"
elif [ -d "$GDRIVE_BASE/My Drive" ]; then
    TARGET_DIR="$GDRIVE_BASE/My Drive"
fi

# コピー実行
if [ -f "$FINAL_FILE" ] && [ -n "$TARGET_DIR" ]; then
    cp "$FINAL_FILE" "$TARGET_DIR/"
    echo "✅ Google Driveバックアップ完了: $TARGET_DIR"
else
    if [ -z "$TARGET_DIR" ]; then
        echo "❌ エラー: Google Driveの同期フォルダが見つかりません。"
    else
        echo "❌ エラー: コピーするファイル ($FINAL_FILE) が存在しません。"
    fi
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ 全工程終了: $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"