#!/bin/bash
# パスを通す
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# ★ここが間違っていたので修正しました (Desktopを削除)
cd /Users/tcrairai_sub/Desktop/card-site-clean

echo "⏰ [Buying] 自動更新を開始します: $(date)" >> buying_log.txt

# Pythonのパスを特定
PYTHON_CMD=$(which python3)

# ==========================================
# 買取データ取得パート
# ==========================================

# buying_scraper.py が実行ファイル名だと仮定しています
# 必要に応じて引数などを調整してください
$PYTHON_CMD buying_scraper.py

# ==========================================
# GitHub送信パート
# ==========================================
git add .

# 変更がある場合のみコミット＆プッシュ
if ! git diff --cached --quiet; then
  git commit -m "🤖 Mac自動更新: 買取データ"
  git pull --rebase
  git push
  echo "✅ [Buying] 送信完了: $(date)" >> buying_log.txt
else
  echo "⚠ [Buying] 変更なし: $(date)" >> buying_log.txt
fi
