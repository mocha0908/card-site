#!/bin/bash

# --- 1. 住所（パス）の設定 ---
# あなたの現在のフォルダ「card-site-clean」に固定します
TARGET_DIR="$HOME/Desktop/card-site-clean"
# Pythonの場所を指定（which python3 の結果）
PYTHON_CMD="/usr/local/bin/python3"

echo "--- 🛠️ 手動更新モード 実行開始 ---"

# --- 2. ディレクトリへ移動 ---
if [ -d "$TARGET_DIR" ]; then
    cd "$TARGET_DIR" || exit 1
    echo "📂 フォルダに移動しました: $(pwd)"
else
    echo "❌ フォルダが見つかりません: $TARGET_DIR"
    exit 1
fi

# --- 3. Pythonスクレイピング実行 ---
echo "🐍 スクレイピングを開始します..."
"$PYTHON_CMD" buying_scraper.py

# 実行結果を確認
if [ $? -eq 0 ]; then
    echo "✅ スクレイピング完了"
else
    echo "❌ スクレイピング中にエラーが発生しました"
    exit 1
fi

# --- 4. Git操作（最新1件のみを維持） ---
echo "📤 GitHubに送信中..."

# 変更をすべて登録
git add .

# 履歴を増やさず、直前のコミットを最新データで「上書き」する
# (--amend は前回の履歴を消して、今のデータに置き換える魔法の言葉です)
git commit --amend -m "🤖 Mac自動更新: $(date +'%Y-%m-%d %H:%M')" --no-edit || \
git commit -m "🤖 初回データ作成: $(date +'%Y-%m-%d %H:%M')"

# GitHubへ強制送信（-f でGitHub側のゴミも一掃します）
if git push -f origin main; then
    echo "✨ 完了！GitHubのデータが最新に置き換わりました"
else
    echo "❌ 送信失敗。ネット接続を確認してください"
    exit 1
fi

echo "--- 🏁 すべての処理が終了しました ---"