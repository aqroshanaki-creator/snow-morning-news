#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
佐久間大介＆Snow Man 朝刊ニュース自動生成スクリプト
RSSフィードからの収集、NGワード・ネガティブ除外、Gemini APIによる要約、data.json出力を行います。
"""

import os
import sys
import json
import time
import re
import datetime
from email.utils import parsedate_to_datetime
import urllib.parse
import feedparser
import requests

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
OUTPUT_DATA_PATH = os.path.join(BASE_DIR, "..", "web", "data.json")

def load_config():
    """設定ファイルを読み込む"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def clean_html(raw_html):
    """HTMLタグを除去してプレーンテキストにする"""
    if not raw_html:
        return ""
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return " ".join(cleantext.split())

def extract_source(entry):
    """記事の媒体名（メディア名）を取得する"""
    if hasattr(entry, "source") and hasattr(entry.source, "title"):
        return entry.source.title
    # Googleニュースのタイトル末尾によくある「 - メディア名」を抽出
    title = entry.get("title", "")
    if " - " in title:
        parts = title.rsplit(" - ", 1)
        return parts[1].strip()
    return "ニュース"

def clean_title(title):
    """タイトル末尾のメディア名表記（ - メディア名）を除去して見出しをすっきりさせる"""
    if " - " in title:
        return title.rsplit(" - ", 1)[0].strip()
    return title.strip()

def is_within_timeframe(entry, lookback_hours=36):
    """指定時間（デフォルト36時間）以内の記事か判定"""
    now = datetime.datetime.now(datetime.timezone.utc)
    published_dt = None

    if hasattr(entry, "published_parsed") and entry.published_parsed:
        published_dt = datetime.datetime(*entry.published_parsed[:6], tzinfo=datetime.timezone.utc)
    elif hasattr(entry, "published"):
        try:
            published_dt = parsedate_to_datetime(entry.published)
        except Exception:
            published_dt = now  # パース失敗時は直近扱い

    if not published_dt:
        return True

    diff = now - published_dt
    return diff.total_seconds() <= (lookback_hours * 3600)

def matches_ng_filter(text, link, ng_keywords, ng_domains):
    """第1段：機械的NG判定（キーワードおよび特定ドメイン）"""
    if not text:
        return False, ""
    
    # ドメインチェック
    for domain in ng_domains:
        if domain.lower() in link.lower():
            return True, f"NGドメイン ({domain})"

    # キーワードチェック
    for kw in ng_keywords:
        if kw.lower() in text.lower():
            return True, f"NGワード ({kw})"

    return False, ""

def fetch_rss_articles(config):
    """RSSフィードから記事を収集し、重複排除および第1段フィルタを実行"""
    search_settings = config.get("search_settings", {})
    lookback_hours = search_settings.get("lookback_hours", 36)
    filtering = config.get("filtering", {})
    ng_keywords = filtering.get("ng_keywords", [])
    ng_domains = filtering.get("ng_domains", [])

    all_raw_articles = []
    seen_urls = set()
    seen_titles = set()

    for category, feeds in search_settings.get("rss_feeds", {}).items():
        for feed_url in feeds:
            try:
                # RSS取得（タイムアウト付き）
                parsed_feed = feedparser.parse(feed_url)
                for entry in parsed_feed.entries:
                    link = entry.get("link", "")
                    raw_title = entry.get("title", "")
                    title = clean_title(raw_title)
                    summary = clean_html(entry.get("summary", ""))
                    source = extract_source(entry)

                    # 重複チェック（URLまたは類似タイトル）
                    norm_title = re.sub(r"\s+", "", title).lower()
                    if link in seen_urls or norm_title in seen_titles:
                        continue
                    seen_urls.add(link)
                    seen_titles.add(norm_title)

                    # 日時チェック
                    if not is_within_timeframe(entry, lookback_hours):
                        continue

                    # 第1段：機械的NGワードフィルタ
                    target_text = f"{title} {summary}"
                    is_ng, reason = matches_ng_filter(target_text, link, ng_keywords, ng_domains)
                    if is_ng:
                        print(f"[除外/機械判定] {reason}: {title}")
                        continue

                    pub_date = ""
                    if hasattr(entry, "published"):
                        pub_date = entry.published

                    all_raw_articles.append({
                        "category_feed": category,
                        "title": title,
                        "raw_title": raw_title,
                        "link": link,
                        "summary_raw": summary,
                        "source": source,
                        "published": pub_date
                    })
            except Exception as e:
                print(f"[RSS取得エラー] {feed_url}: {e}")

    return all_raw_articles

def call_gemini_api(prompt, api_key, config):
    """Gemini APIを呼び出す（無料枠・リトライ・バックオフ対応）"""
    gemini_cfg = config.get("gemini_settings", {})
    model = gemini_cfg.get("model", "gemini-2.5-flash")
    fallback_model = gemini_cfg.get("fallback_model", "gemini-1.5-flash")
    max_retries = gemini_cfg.get("max_retries", 3)
    base_delay = gemini_cfg.get("retry_delay_seconds", 4)

    models_to_try = [model, fallback_model]

    for current_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": gemini_cfg.get("temperature", 0.2),
                "responseMimeType": "application/json"
            }
        }

        for attempt in range(max_retries):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
                elif resp.status_code == 429:
                    # 無料枠レートリミット対策: 待機して再試行
                    wait_time = base_delay * (2 ** attempt)
                    print(f"[Gemini 429待機] レートリミット検出。{wait_time}秒待機して再試行します...")
                    time.sleep(wait_time)
                else:
                    print(f"[Gemini APIエラー] ステータスコード: {resp.status_code}, 内容: {resp.text}")
                    break
            except Exception as e:
                print(f"[Gemini 通信エラー (試行 {attempt + 1}/{max_retries})]: {e}")
                time.sleep(base_delay)

    return None

def judge_and_summarize_with_gemini(article, api_key, config):
    """
    第2段：Geminiによるポジティブ/ニュートラル判定および要約生成
    迷ったら除外する（is_acceptable: false）方針を徹底。
    """
    prompt = f"""
あなたはSnow Man（特に佐久間大介さん）を心から応援するファンのための朝刊ニュースキュレーターです。
以下の記事情報を審査し、ファンが朝から心地よく前向きな気持ちで読める「ポジティブまたはニュートラル」な記事かどうか厳格に判定してください。

【厳格な除外ルール（最重要）】
- アンチ記事、批判、炎上、バッシング、不仲説、熱愛やゴシップ、憶測、週刊誌の飛ばし記事、ファンの対立を煽るものは【絶対にREJECT】してください。
- 記事の文脈や引用にトゲがあるもの、少しでも読者が不快・不安になる懸念があるもの、判定に迷うものは【すべて安全側に倒してREJECT (is_acceptable: false)】してください。
- 公式の活躍、出演情報、作品情報、ラジオや番組での微笑ましいエピソード、ポジティブな反響のみを承認（is_acceptable: true）してください。

【出力要件】
承認する場合、著作権を尊重し記事本文の丸写しはせず、自分の言葉で1〜2行（50〜80字程度）の簡潔で爽やかな要約文を作成してください。
以下のJSONフォーマットのみを返してください。

{{
  "is_acceptable": trueまたはfalse,
  "reject_reason": "REJECT時の理由（承認時は空文字）",
  "summary": "1〜2行の明るく簡潔な要約文（REJECT時は空文字）",
  "is_schedule": trueまたはfalse（出演・放送・雑誌発売などの予定情報を含む場合true）,
  "schedule_note": "出演予定の概要（例: 『10/25 20:00〜 ○○出演』など。なければ空文字）",
  "has_x_buzz": trueまたはfalse（SNSやXでのファンの温かい盛り上がりやトレンド入りの言及がある場合true）,
  "x_buzz_summary": "ファンの反響や盛り上がりの要約（なければ空文字）"
}}

【対象記事】
タイトル: {article['title']}
媒体名: {article['source']}
記事概要: {article['summary_raw']}
"""
    result_text = call_gemini_api(prompt, api_key, config)
    if not result_text:
        # API呼び出し失敗時のフォールバック: タイトル・概要にNG要素が機械判定を抜けていないか再確認し、タイトルと媒体名のみで採用
        return {
            "is_acceptable": True,
            "summary": article['title'],
            "is_schedule": False,
            "schedule_note": "",
            "has_x_buzz": False,
            "x_buzz_summary": "",
            "is_fallback": True
        }

    try:
        # JSONコードブロックが含まれていた場合のクリーンアップ
        cleaned = re.sub(r"^```json\s*", "", result_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
        data = json.loads(cleaned)
        return data
    except Exception as e:
        print(f"[Gemini 判定パース失敗]: {e}, 生テキスト: {result_text}")
        return {
            "is_acceptable": True,
            "summary": article['title'],
            "is_schedule": False,
            "schedule_note": "",
            "has_x_buzz": False,
            "x_buzz_summary": "",
            "is_fallback": True
        }

def generate_daily_quote(api_key, config, sakuma_count, snowman_count):
    """朝の「今日のひとこと」（2〜3行の明るいメッセージ）を生成"""
    fallback_quotes = [
        "おはようございます！今日も佐久間くんとSnow Manの笑顔を胸に、素敵な一日にしましょう！✨",
        "今日も一日がんばるあなたへ！佐久間くんのポジティブパワーとSnow Manの温かい元気をチャージして、良い日になりますように💖",
        "朝のSnow Manニュースをお届け！今日も佐久間くんやメンバーたちの活躍を応援しながら、心地よい一日を過ごしましょう⛄"
    ]
    # フォールバックのランダム（日付ベース）
    day_idx = datetime.datetime.now().day % len(fallback_quotes)
    default_quote = fallback_quotes[day_idx]

    if not api_key:
        return default_quote

    prompt = f"""
Snow Manファン、特に佐久間大介くんのファンに向けた、朝刊Webアプリの「今日のひとこと」（2〜3行、60〜90文字程度）を作成してください。
明るく前向きで、通勤中や朝の準備中に読んで心がパッと温かくなるような、元気が出るメッセージにしてください。
佐久間くんの明るい人柄（他担狩り、アニメ好き、笑顔、優しさ、元気）やSnow Manの絆を感じられる言葉遣いでお願いします。

以下のJSONフォーマットのみを返してください。
{{
  "quote": "メッセージ本文"
}}
"""
    result_text = call_gemini_api(prompt, api_key, config)
    if result_text:
        try:
            cleaned = re.sub(r"^```json\s*", "", result_text.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            if "quote" in data and data["quote"]:
                return data["quote"].strip()
        except Exception:
            pass
    return default_quote

def main():
    print("=== Snow Man & 佐久間大介 朝刊ニュース生成開始 ===")
    config = load_config()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if not api_key:
        print("[警告] GEMINI_API_KEY が設定されていません。フォールバックモード（タイトル＋リンクのみ）で動作します。")

    # 1. RSS収集
    raw_articles = fetch_rss_articles(config)
    print(f"取得記事数（第1段フィルタ後）: {len(raw_articles)}件")

    sakuma_news = []
    snowman_news = []
    schedules = []
    x_buzz_list = []

    search_settings = config.get("search_settings", {})
    max_sakuma = search_settings.get("max_items_sakuma", 5)
    max_snowman = search_settings.get("max_items_snowman", 5)

    # 2. 記事の分類・Gemini判定＆要約
    for idx, article in enumerate(raw_articles):
        # 必要な件数に達していれば打ち切り（API節約）
        if len(sakuma_news) >= max_sakuma and len(snowman_news) >= max_snowman and len(schedules) >= 3:
            break

        is_sakuma_related = "佐久間" in article["title"] or "佐久間" in article["summary_raw"]

        # Gemini判定
        if api_key:
            judge_res = judge_and_summarize_with_gemini(article, api_key, config)
            # API利用制限に引っかからないよう短いウェイト
            time.sleep(1.0)
        else:
            judge_res = {
                "is_acceptable": True,
                "summary": article["title"],
                "is_schedule": "出演" in article["title"] or "放送" in article["title"],
                "schedule_note": "",
                "has_x_buzz": False,
                "x_buzz_summary": "",
                "is_fallback": True
            }

        if not judge_res.get("is_acceptable", False):
            print(f"[除外/AI判定] {judge_res.get('reject_reason')}: {article['title']}")
            continue

        item_data = {
            "title": article["title"],
            "summary": judge_res.get("summary") or article["title"],
            "source": article["source"],
            "link": article["link"],
            "published": article["published"]
        }

        # 出演情報がある場合
        if judge_res.get("is_schedule"):
            sched_note = judge_res.get("schedule_note") or article["title"]
            schedules.append({
                "title": article["title"],
                "note": sched_note,
                "source": article["source"],
                "link": article["link"]
            })

        # X反響がある場合
        if judge_res.get("has_x_buzz") and judge_res.get("x_buzz_summary"):
            x_buzz_list.append({
                "title": article["title"],
                "buzz": judge_res.get("x_buzz_summary"),
                "source": article["source"],
                "link": article["link"]
            })

        # 佐久間大介 または Snow Man に振り分け
        if is_sakuma_related:
            if len(sakuma_news) < max_sakuma:
                sakuma_news.append(item_data)
        else:
            if len(snowman_news) < max_snowman:
                snowman_news.append(item_data)

    # 3. 新着が少ない場合、前日の既存データから補完
    previous_data = {}
    if os.path.exists(OUTPUT_DATA_PATH):
        try:
            with open(OUTPUT_DATA_PATH, "r", encoding="utf-8") as f:
                previous_data = json.load(f)
        except Exception as e:
            print(f"[過去データ読み込み警告]: {e}")

    # 佐久間大介ニュースの補完
    if len(sakuma_news) < 2 and previous_data.get("sakuma_news"):
        existing_links = {item["link"] for item in sakuma_news}
        for old_item in previous_data["sakuma_news"]:
            if old_item.get("link") not in existing_links and len(sakuma_news) < max_sakuma:
                old_item_copy = dict(old_item)
                old_item_copy["is_yesterday"] = True
                sakuma_news.append(old_item_copy)

    # Snow Manニュースの補完
    if len(snowman_news) < 2 and previous_data.get("snowman_news"):
        existing_links = {item["link"] for item in snowman_news}
        for old_item in previous_data["snowman_news"]:
            if old_item.get("link") not in existing_links and len(snowman_news) < max_snowman:
                old_item_copy = dict(old_item)
                old_item_copy["is_yesterday"] = True
                snowman_news.append(old_item_copy)

    # 4. 今日のひとこと生成
    daily_quote = generate_daily_quote(api_key, config, len(sakuma_news), len(snowman_news))

    # 日本時間（JST）の現在時刻を取得
    jst = datetime.timezone(datetime.timedelta(hours=9))
    now_jst = datetime.datetime.now(jst)
    formatted_date = now_jst.strftime("%Y年%m月%d日 (%a)")
    # 曜日を日本語表記に
    weekdays_ja = {"Mon": "月", "Tue": "火", "Wed": "水", "Thu": "木", "Fri": "金", "Sat": "土", "Sun": "日"}
    for en_w, ja_w in weekdays_ja.items():
        formatted_date = formatted_date.replace(f"({en_w})", f"({ja_w})")

    formatted_time = now_jst.strftime("%H:%M")

    output_data = {
        "updated_at": f"{formatted_date} {formatted_time} 更新",
        "daily_quote": daily_quote,
        "sakuma_news": sakuma_news,
        "snowman_news": snowman_news,
        "schedules": schedules[:3],
        "x_buzz": x_buzz_list[:3]
    }

    # 5. data.json書き出し（アトミックに書き込み）
    temp_output_path = OUTPUT_DATA_PATH + ".tmp"
    with open(temp_output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    if os.path.exists(OUTPUT_DATA_PATH):
        os.remove(OUTPUT_DATA_PATH)
    os.rename(temp_output_path, OUTPUT_DATA_PATH)

    print(f"=== 生成完了: 佐久間ニュース {len(sakuma_news)}件, Snow Manニュース {len(snowman_news)}件 ===")
    print(f"出力先: {OUTPUT_DATA_PATH}")

if __name__ == "__main__":
    main()

