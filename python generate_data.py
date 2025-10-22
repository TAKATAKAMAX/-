import requests
import random
import json
import os
from datetime import datetime, timedelta
import re # HTMLファイル削除のために正規表現を使用

# =====================
# 環境変数から取得
# =====================
# DMM APIのIDとアフィリエイトIDをGitHub Secretsなどの環境変数から取得します
DMM_API_ID = os.getenv("DMM_API_ID")
DMM_AFFILIATE_ID = os.getenv("DMM_AFFILIATE_ID")

if not DMM_API_ID or not DMM_AFFILIATE_ID:
    raise ValueError("⚠️ DMM_API_ID または DMM_AFFILIATE_ID が設定されていません。")

# =====================
# DMMから商品を取得
# =====================
def get_dmm_items(keyword, count):
    url = "https://api.dmm.com/affiliate/v3/ItemList"
    params = {
        "api_id": DMM_API_ID,
        "affiliate_id": DMM_AFFILIATE_ID,
        "site": "DMM.com",
        "service": "mono", # アダルト商品除外のため'mono'に限定
        "keyword": keyword,
        "hits": 30,
        "sort": "rank"
    }

    response = requests.get(url, params=params)
    data = response.json()

    items = []
    if "result" in data and "items" in data["result"]:
        for item in data["result"]["items"]:
            price = item.get("prices", {}).get("price", "不明")
            try:
                # 価格が数字として扱えるかチェック
                int(price)
            except ValueError:
                # 数字でない場合はそのままの値（例: "要問い合わせ"）を保持
                price = item.get("prices", {}).get("price", "不明")
            
            items.append({
                "title": item.get("title", "不明"),
                "url": item.get("URL", ""),
                "image": item.get("imageURL", {}).get("large", ""),
                "price": price,
                "source": "DMM"
            })
    else:
        print(f"⚠️ DMM APIからitemsが返ってきませんでした (キーワード: {keyword})")

    return items

# =====================
# 履歴を管理・自動削除する関数 (データ削除)
# =====================
def update_history(new_items, target_count=5):
    HISTORY_FILE = "history.json"
    MAX_DAYS = 30  # 30日分を保存

    # 1. 既存の履歴を読み込む
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ 履歴ファイルが破損しているため、新しく作成します。")
            history = []
    else:
        history = []
    
    today = datetime.now().strftime("%Y/%m/%d")
    # HTMLファイル名 (例: recommend_20251021.html)
    today_filename = datetime.now().strftime("recommend_%Y%m%d.html")
    
    # 2. 過去30日以前のデータを削除 (自動削除)
    cutoff_date = datetime.now() - timedelta(days=MAX_DAYS)
    
    new_history = []
    for entry in history:
        try:
            entry_date = datetime.strptime(entry["date"], "%Y/%m/%d")
            # 30日以内のデータのみ残す
            if entry_date >= cutoff_date:
                new_history.append(entry)
        except ValueError:
            # 日付形式が不正なエントリは残さない
            continue

    # 3. 今日のデータを追加
    # 当日のランダムな商品5件を抽出
    num_to_sample = min(target_count, len(new_items))
    display_items = random.sample(new_items, num_to_sample) if num_to_sample > 0 else []

    today_entry = {
        "date": today,
        "filename": today_filename, # HTML生成スクリプトで使用
        "items": display_items
    }
    
    # すでに今日のエントリがあれば削除してから追加 (二重実行対策)
    new_history = [e for e in new_history if e["date"] != today]
    new_history.insert(0, today_entry) # 最新のものをリストの先頭に追加

    # 4. 履歴を保存
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)
        
    print(f"✅ history.json を更新しました。現在 {len(new_history)} 日分の履歴があります。")
    return today_entry["items"] # 今日のオススメ（5件）を返す

# =====================
# HTMLファイルを自動削除する関数 (物理ファイル削除)
# =====================
def cleanup_old_html_files():
    MAX_DAYS = 30
    # 削除対象となる日付の境界線
    cutoff_date = datetime.now() - timedelta(days=MAX_DAYS)
    # ファイル名から日付を抽出するための正規表現 (例: recommend_YYYYMMDD.html)
    date_pattern = re.compile(r'recommend_(\d{8})\.html')
    
    deleted_count = 0
    
    # スクリプトがあるディレクトリのファイルをチェック
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    for filename in os.listdir(current_dir):
        match = date_pattern.match(filename)
        
        # 1. ファイル名がパターンにマッチするか確認
        if match:
            date_str = match.group(1) # YYYYMMDD 形式の文字列を取得
            
            try:
                # 2. ファイル名から日付をパース
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                # 3. 30日以上前の日付か確認
                if file_date < cutoff_date:
                    file_path = os.path.join(current_dir, filename)
                    os.remove(file_path) # ファイルを削除
                    print(f"  -> 古いHTMLファイルを削除: {filename}")
                    deleted_count += 1
            except ValueError:
                # 日付形式が不正なファイルはスキップ
                continue
                
    if deleted_count > 0:
        print(f"✅ 古いHTMLファイル {deleted_count} 件を削除しました。")
    else:
        print("✅ 削除対象の古いHTMLファイルはありませんでした。")


# =====================
# JSONとして保存 (メイン処理)
# =====================
def save_items_to_json():
    # 複数の検索キーワード
    keywords = ["イヌ関連", "ネコ関連", "ペット用品", "ペット","イヌ","ネコ","おやつ","ペットおもちゃ"]
    all_items = []
    
    # 複数のキーワードで商品を取得し、統合
    for keyword in keywords:
        dmm_items = get_dmm_items(keyword=keyword, count=10) 
        all_items.extend(dmm_items)
        
    # 重複を排除 (URLをキーとして使用)
    unique_items = list({item['url']: item for item in all_items}.values())

    if not unique_items:
        print("❌ 全キーワードで商品を取得できませんでした。")
        return

    # 履歴の更新と、今日のオススメ5件の取得 (history.jsonのデータ削除)
    today_recommendations = update_history(unique_items, target_count=5)
    
    # current_week.json は「今日のオススメ」5件のみを保存
    with open("current_week.json", "w", encoding="utf-8") as f:
        json.dump(today_recommendations, f, ensure_ascii=False, indent=2)

    print(f"✅ current_week.json を作成しました！（{len(today_recommendations)}件）")
    
    # 履歴データ削除後に、物理ファイルも削除する処理を実行
    cleanup_old_html_files()


if __name__ == "__main__":
    save_items_to_json()