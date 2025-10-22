import json
import os
from datetime import datetime, timedelta

def update_and_get_history(new_recommendations):
    """
    履歴ファイル (history.json) を読み込み、新しいエントリを追加し、
    30日以上前の古いデータを削除してファイルを更新します。

    Args:
        new_recommendations (list): 今日のオススメ商品リスト（dictのリスト）。
    
    Returns:
        list: 更新後の全履歴リスト。
    """
    HISTORY_FILE = "history.json"
    MAX_DAYS = 30  # 履歴を保持する最大日数

    # 1. 既存の履歴を読み込む (ファイルがなければ空のリストから開始)
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ 履歴ファイルが破損しています。新しく作成します。")
            history = []
    else:
        history = []
    
    today = datetime.now().strftime("%Y/%m/%d")
    today_filename = datetime.now().strftime("recommend_%Y%m%d.json")
    
    # 2. 過去のデータを自動削除 (30日ルール)
    cutoff_date = datetime.now() - timedelta(days=MAX_DAYS)
    
    new_history = []
    for entry in history:
        try:
            entry_date = datetime.strptime(entry["date"], "%Y/%m/%d")
            # 30日以内のデータのみ残す
            if entry_date >= cutoff_date:
                new_history.append(entry)
        except ValueError:
            # 日付形式が不正なエントリはスキップ
            continue

    # 3. 今日のデータを追加
    today_entry = {
        "date": today,
        "filename": today_filename, # 今日のオススメのファイル名 (必須ではないが、構造に合わせる)
        "items": new_recommendations # 今日のオススメ商品データ
    }
    
    # すでに今日のエントリがあれば削除してから追加 (スクリプトの二重実行対策)
    new_history = [e for e in new_history if e["date"] != today]
    new_history.insert(0, today_entry) # 最新のものをリストの先頭に追加

    # 4. 履歴をファイルに保存
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)
        
    print(f"✅ {HISTORY_FILE} を更新しました。現在 {len(new_history)} 日分の履歴があります。")
    return new_history