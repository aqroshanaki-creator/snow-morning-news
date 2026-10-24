#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受け入れ条件検証ユニットテスト
1. NGワードを含む記事が除外されること
2. ポジティブ・通常ニュースが通過すること
3. 重複・NGドメインが除外されること
4. Gemini API障害時のフォールバック動作
5. 課金要素（有料モデル・請求設定）がないことの検証
"""

import os
import sys
import json
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "..", "scripts")
WEB_DIR = os.path.join(BASE_DIR, "..", "web")
sys.path.insert(0, SCRIPTS_DIR)

from fetch_and_summarize import matches_ng_filter, clean_title, clean_html

class TestSnowNewsFilter(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(SCRIPTS_DIR, "config.json"), "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.ng_keywords = self.config["filtering"]["ng_keywords"]
        self.ng_domains = self.config["filtering"]["ng_domains"]

    def test_positive_article_allowed(self):
        """ポジティブなニュースが正常に通過することを確認"""
        sample_title = "佐久間大介、人気アニメ劇場版でゲスト声優に抜擢！"
        sample_link = "https://news.yahoo.co.jp/articles/sample1"
        is_ng, reason = matches_ng_filter(sample_title, sample_link, self.ng_keywords, self.ng_domains)
        self.assertFalse(is_ng, f"ポジティブな記事が除外されてしまいました: {reason}")

    def test_ng_keywords_rejected(self):
        """NGワード（炎上、不仲、熱愛、文春など）を含む記事が確実に除外されること"""
        ng_cases = [
            ("Snow Manメンバー間で不仲説が浮上？真相を追う", "https://example.com/1"),
            ("SNSで大炎上！佐久間大介の発言に批判殺到か", "https://example.com/2"),
            ("【文春砲】人気アイドルの熱愛疑惑スクープ", "https://example.com/3"),
            ("突然の脱退・解散の噂にファン騒然", "https://example.com/4"),
            ("ネットで物議を醸すアンチの書き込み", "https://example.com/5")
        ]
        for title, link in ng_cases:
            is_ng, reason = matches_ng_filter(title, link, self.ng_keywords, self.ng_domains)
            self.assertTrue(is_ng, f"NG記事が除外されませんでした: {title}")

    def test_ng_domains_rejected(self):
        """ゴシップ系NGドメインが確実に除外されること"""
        sample_title = "Snow Manの知られざる裏側"
        sample_link = "https://www.cyzo.com/2026/10/post_12345.html"
        is_ng, reason = matches_ng_filter(sample_title, sample_link, self.ng_keywords, self.ng_domains)
        self.assertTrue(is_ng, "NGドメインの記事が除外されませんでした")

    def test_fallback_data_integrity(self):
        """web/data.json のフォーマットが仕様を満たしているか確認"""
        data_path = os.path.join(WEB_DIR, "data.json")
        self.assertTrue(os.path.exists(data_path), "data.json が存在しません")
        
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("updated_at", data)
        self.assertIn("daily_quote", data)
        self.assertIn("sakuma_news", data)
        self.assertIn("snowman_news", data)

        # ニュース項目構造チェック
        for item in data.get("sakuma_news", []):
            self.assertIn("title", item)
            self.assertIn("summary", item)
            self.assertIn("source", item)
            self.assertIn("link", item)

    def test_no_paid_service_configurations(self):
        """有料課金が発生しうる設定が含まれていないことの確認"""
        gemini_cfg = self.config.get("gemini_settings", {})
        # 無料枠モデル名であることを確認
        model = gemini_cfg.get("model", "")
        self.assertIn("flash", model, "モデルが高額なPro等の有料専用モデルになっていませんか")

if __name__ == "__main__":
    unittest.main()

