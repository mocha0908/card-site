#!/bin/bash
cd /Users/tcrairai_sub/Desktop/card-site

echo "🚀 販売データの更新を開始します（全件取得モード）..."

# Pythonの場所を自動取得して実行

# 1. AR (上書き)
$(which python3) scraper.py --keyword "AR" --mode overwrite

# 2. CHR (追記)
$(which python3) scraper.py --keyword "CHR" --mode append

# 3. SAR (追記)
$(which python3) scraper.py --keyword "SAR" --mode append

# 4. SR (追記)
$(which python3) scraper.py --keyword "SR" --mode append

# 5. HR (追記)
$(which python3) scraper.py --keyword "HR" --mode append

# GitHubへ送信
git add card_data.csv
git commit -m "Macから販売データを更新"
git pull --rebase
git push
