#!/bin/bash
# フォルダに移動（念のため絶対パスで指定）
cd /Users/tcrairai_sub/Desktop/card-site

# スクレイピング実行
# python3のパスは環境によって違う場合があるため、標準的なパスを指定
/usr/bin/python3 buying_scraper.py

# GitHubへアップロード
git add buying_data.csv
git commit -m "Auto update from Mac"
git pull --rebase
git push#!/bin/bash
# 念のため、実行時もフォルダを移動
cd /Users/tcrairai_sub/Desktop/card-site

# Python実行 (python3の場所を自動検知して実行)
$(which python3) buying_scraper.py

# GitHubへ送信
git add buying_data.csv
git commit -m "Auto update from Mac"
git pull --rebase
git push
