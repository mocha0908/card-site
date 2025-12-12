#!/bin/bash
cd /Users/tcrairai_sub/Desktop/card-site

echo "🚀 販売データの更新を開始します..."

# 1. AR (上書き)
/usr/bin/python3 scraper.py --keyword "AR" --mode overwrite --end-page 15

# 2. CHR (追記)
/usr/bin/python3 scraper.py --keyword "CHR" --mode append --end-page 15

# 3. SAR (追記)
/usr/bin/python3 scraper.py --keyword "SAR" --mode append --end-page 15

# 4. SR (追記)
/usr/bin/python3 scraper.py --keyword "SR" --mode append --end-page 15

# 5. HR (追記)
/usr/bin/python3 scraper.py --keyword "HR" --mode append --end-page 15

# GitHubへ送信
git add card_data.csv
git commit -m "Macから販売データを更新"
git pull --rebase
git push
