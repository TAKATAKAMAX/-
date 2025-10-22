import json
import random
import os
from openai import OpenAI
from google import generativeai 
from datetime import datetime 

# ======================
# 環境変数からAPIキー取得
# ======================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not OPENAI_API_KEY and not GOOGLE_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY または GOOGLE_API_KEY が設定されていません。")

# ======================
# クライアント初期化
# ======================
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Gemini API設定: Clientを使わず、AttributeErrorを回避するためconfigureを使用
gemini_ready = False
if GOOGLE_API_KEY:
    try:
        generativeai.configure(api_key=GOOGLE_API_KEY)
        gemini_ready = True
    except Exception as e:
        print(f"⚠️ Gemini API設定エラー: {e}")
        gemini_ready = False

# スクリプトのディレクトリパスをグローバルに取得
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE_NAME = "history.json"
CURRENT_WEEK_FILE_NAME = "current_week.json"

# ======================
# 過去のオススメHTML生成 (パス修正済み)
# ======================
def generate_history_html():
    history_file_path = os.path.join(SCRIPT_DIR, HISTORY_FILE_NAME)
    history_html = '<div class="history-list">\n'
    
    if os.path.exists(history_file_path):
        try:
            with open(history_file_path, "r", encoding="utf-8") as f:
                history = json.load(f)
            
            history_html += '<h3>過去のオススメ</h3>\n'
            display_limit = 30
            
            for entry in history[:display_limit]:
                link_url = entry.get("filename", "index.html")
                history_html += f'  <p class="history-date"><a href="{link_url}">{entry["date"]}</a></p>\n' 
            
            if len(history) > display_limit:
                 history_html += f'  <p class="history-date history-more">... 他 {len(history) - display_limit}日分</p>\n'
                 
        except Exception as e:
            history_html += f'<p>履歴の読み込みエラー: {e}</p>'
    else:
        history_html += '<p>過去のオススメ履歴はありません。</p>'
        
    history_html += '</div>\n'
    return history_html

# ======================
# AIで紹介文生成 (省略なし)
# ======================
def generate_description(title):
    prompt = f"商品タイトル: {title}\nこの商品を魅力的に紹介する短い文章を日本語で作ってください。"

    if openai_client:
        try:
            print(f"🧠 ChatGPTで生成中: {title}")
            res = openai_client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ ChatGPTエラー発生（Geminiへ切り替え）: {e}")

    if gemini_ready:
        try:
            print(f"✨ Geminiで生成中: {title}")
            res = generativeai.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt
            )
            return res.text.strip()
        except Exception as e:
            print(f"⚠️ Geminiエラー: {e}")

    return "説明文を生成できませんでした。"

# =========================================================
# 日ごとの履歴HTMLを生成する関数 (generate_daily_html)
# =========================================================
def generate_daily_html(items, page_title, filename_with_path, history_sidebar):
    
    # HTMLの共通ヘッダー部分
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>{page_title}</title>
    <style>
        /* ==================== */
        /* ★★★ ヘッダー部分のスタイル (背景色削除済み) ★★★ */
        /* ==================== */
        .header-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }}
        .header-title-box {{
            border: 3px solid #000;
            padding: 10px 30px;
            margin: 0 20px;
            text-align: center;
            flex-grow: 1;
        }}
        .header-title-box h1 {{
            margin: 0;
            font-size: 2em;
        }}
        .header-image {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            /* ★★★ ここを削除！ ★★★ */
            /* background-color: #4A86E8; */ 
            border: 2px solid #000;
            overflow: hidden; 
        }}
        .header-image img {{
            width: 100%;
            height: 100%;
            object-fit: cover; 
            display: block;
        }}
        /* ==================== */
        
        body {{ font-family: sans-serif; }}
        #container {{ width: 90%; max-width: 1000px; margin: 20px auto; display: flex; border: 1px solid #ddd; padding: 10px; }}
        #sidebar {{ width: 220px; padding: 10px 15px; border-right: 1px solid #eee; margin-right: 20px; }}
        #main-content {{ flex-grow: 1; }}
        
        .history-list h3 {{ margin-top: 0; border-bottom: 2px solid #ccc; padding-bottom: 5px; }}
        .history-date {{ font-size: 0.9em; margin: 3px 0; }}
        .history-date a {{ color: #007bff; text-decoration: none; }}
        .history-date.history-more {{ font-style: italic; color: #888; }}

        ul {{ list-style-type: none; padding: 0; }}
        li {{ border-bottom: 1px solid #ccc; margin-bottom: 20px; padding: 15px 0; }}
        img {{ display: block; margin: 10px 0; border-radius: 4px; max-width: 150px; height: auto; }}
        p {{ margin: 5px 0; }}
        .price {{ font-weight: bold; color: #E91E63; font-size: 1.1em; }}
    </style>
</head>
<body>

<div class="header-container">
    <div class="header-image">
        <img src="header_left.jpg" alt="サイトイメージ画像 左">
    </div>
    <div class="header-title-box">
        <h1>わんニャン！アフェリペット</h1> 
    </div>
    <div class="header-image">
        <img src="header_right.jpg" alt="サイトイメージ画像 右">
    </div>
</div>
<div id="container">
    <div id="sidebar">
        {history_sidebar}
    </div>
    <div id="main-content">
        <h2>{page_title}</h2>
        <p class="recommend-label">今週のオススメ</p>
        <ul>
"""
    
    # 商品リストのループ
    for item in items:
        # --- 価格表示の修正（カンマと「円」の追加） ---
        formatted_price = item.get('price', '価格不明') 
        try:
            price_value = int(item['price'])
            formatted_price = f"{price_value:,}円"
        except (ValueError, TypeError):
            pass 

        # 紹介文を生成
        desc = generate_description(item['title'])
        
        html_content += f"""
        <li>
            <h2>{item['title']}</h2>
            <a href="{item['url']}" target="_blank">
                <img src="{item['image']}" alt="{item['title']}" width="150">
            </a>
            <p class="price">価格: {formatted_price}</p>
            <p>{desc}</p>
            <p><a href="{item['url']}" target="_blank">商品ページへ</a></p>
        </li>
        """

    html_content += """
        </ul>
    </div>
</div>
</body>
</html>"""

    # 結合済みのパス (filename_with_path) を使用して保存
    with open(filename_with_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ {filename_with_path} を生成しました！")


# ======================
# メイン処理
# ======================
if __name__ == "__main__":
    
    # 1. 履歴情報と今日のオススメを取得
    HISTORY_FILE_PATH = os.path.join(SCRIPT_DIR, HISTORY_FILE_NAME)
    try:
        with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
            history_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history_data = []

    # current_week.jsonから今日のオススメ（トップページ用）を取得
    CURRENT_WEEK_FILE_PATH = os.path.join(SCRIPT_DIR, CURRENT_WEEK_FILE_NAME)
    try:
        with open(CURRENT_WEEK_FILE_PATH, "r", encoding="utf-8") as f:
            today_items = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        today_items = []

    # 2. 過去のオススメHTMLをすべて生成 (サイドバーも同時に生成)
    history_sidebar_html = generate_history_html() 

    if history_data:
        for entry in history_data:
            # 日付ごとの商品ページを生成
            raw_filename = entry.get("filename", f"recommend_{entry['date'].replace('/', '')}.html")
            
            # 履歴ファイルの保存パスを結合
            filename_with_path = os.path.join(SCRIPT_DIR, raw_filename) 
            page_title = f"{entry['date']} のおすすめペット商品"
            
            generate_daily_html(entry['items'], page_title, filename_with_path, history_sidebar_html)

    # 3. トップページ (index.html) の生成
    if today_items:
        # index.html の保存パスを結合
        index_filename_with_path = os.path.join(SCRIPT_DIR, "index.html")
        
        generate_daily_html(today_items, "今週のおすすめペット商品", index_filename_with_path, history_sidebar_html)
    else:
        print("⚠️ トップページに表示する商品がないため、index.htmlは生成されませんでした。")