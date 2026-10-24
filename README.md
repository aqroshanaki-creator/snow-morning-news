# ❄️ Snow Morning News (佐久間大介 ＆ Snow Man 朝刊Webアプリ)

Snow Man（特に佐久間大介さん）の最新ニュースを毎朝自動でまとめ、iPhoneで快適に読めるPWA対応Webアプリです。

- **毎朝自動更新**: GitHub Actions（cron）が日本時間 6:00 に自動実行。
- **完全無料・クレカ不要**: GitHub Pages ＋ Google AI Studio (Gemini API無料枠)。
- **ネガティブ完全除外**: NGワード自動フィルタ ＋ Geminiによるポジティブ審査の二段構え。
- **スマホ特化**: 片手で3分で読み切れる大きめカードUI、ダークモード、オフライン対応PWA。

---

## 📁 ディレクトリ構成

```text
snow-morning-news/
├── .github/
│   └── workflows/
│       └── update_news.yml      # 毎朝6:00自動更新ワークフロー
├── scripts/
│   ├── fetch_and_summarize.py   # ニュース収集・要約・フィルタ実行スクリプト
│   ├── config.json              # 検索キーワード・NGワード等の設定ファイル
│   └── generate_icons.ps1       # アイコン生成用補助スクリプト
├── web/
│   ├── index.html               # アプリ画面本体
│   ├── style.css                # スタイルシート（佐久間くんピンク＆ダークモード）
│   ├── app.js                   # 画面制御・データ描画
│   ├── manifest.json            # PWAマニフェスト
│   ├── sw.js                    # サービスワーカー（オフラインキャッシュ）
│   ├── data.json                # ニュースデータ
│   └── icons/                   # アプリアイコン（SVG/PNG）
├── tests/
│   ├── test_filter.py           # Python単体テスト
│   ├── test_data.json           # テスト用ダミーデータ
│   └── verify_acceptance.ps1    # 受入条件自動検証スクリプト
└── requirements.txt             # 依存ライブラリ一覧
```

---

## 🛠️ 初心者向けセットアップ手順（完全ガイド）

### 【ステップ1】GitHubリポジトリの作成
1. [GitHub](https://github.com/) にログイン（無料アカウント）。
2. 右上の「＋」アイコンから **「New repository」** をクリック。
3. Repository name に `snow-morning-news` と入力。
4. 公開設定を **「Public」** に設定（GitHub Pagesの無料利用に必要です）。
5. 「Create repository」をクリック。

### 【ステップ2】コードをGitHubにアップロード（プッシュ）
作成したフォルダ `C:\Users\hanak\.gemini\antigravity\scratch\snow-morning-news` のファイルを、GitまたはGitHubの画面からアップロードします。

```bash
cd C:\Users\hanak\.gemini\antigravity\scratch\snow-morning-news
git init
git add .
git commit -m "feat: 初回デプロイ"
git branch -M main
git remote add origin https://github.com/<あなたのユーザー名>/snow-morning-news.git
git push -u origin main
```
*(Gitコマンドが難しい場合は、GitHubのWeb画面から「uploading an existing file」を選んで全ファイルをドラッグ＆ドロップでもアップロードできます)*

### 【ステップ3】Gemini APIキーの取得（クレジットカード登録不要・完全無料）
1. [Google AI Studio](https://aistudio.google.com/) にアクセスし、Googleアカウントでログイン。
2. 左上の **「Get API key」** ボタンをクリック。
3. **「Create API key」** をクリックして新しいキーを生成。
4. 表示された英数字のキーをコピー（※このキーは誰にも見せないでください）。

### 【ステップ4】GitHub Secrets（シークレット）にAPIキーを登録
1. GitHubの `snow-morning-news` リポジトリを開く。
2. 上部タブの **「Settings」**（歯車アイコン）をクリック。
3. 左サイドメニューの **「Secrets and variables」** → **「Actions」** をクリック。
4. 緑色の **「New repository secret」** ボタンをクリック。
5. 入力画面で以下のように登録：
   - **Name**: `GEMINI_API_KEY`
   - **Secret**: （ステップ3でコピーしたGeminiのAPIキーを貼り付け）
6. **「Add secret」** をクリックして完了。

### 【ステップ5】GitHub Pagesの有効化
1. リポジトリの **「Settings」** → 左メニューの **「Pages」** を開く。
2. **Build and deployment** の **Source** で **「GitHub Actions」** を選択。
   *(※「Deploy from a branch」にする場合は、Branchを `main`、フォルダを `/web` に指定してSave)*
3. 設定後、ページ上部にあなたの専用URL（例: `https://<ユーザー名>.github.io/snow-morning-news/`）が表示されます。

### 【ステップ6】GitHub Actionsの手動テスト実行
1. リポジトリの上部タブ **「Actions」** をクリック。
2. 左側のワークフロー一覧から **「Update Snow Man Morning News」** を選択。
3. 右側にある **「Run workflow」** ドロップダウンをクリックし、緑色の **「Run workflow」** ボタンを押す。
4. 数分待つとチェックマーク（緑）が付き、GitHub Pagesに最新ニュースが自動反映されます。
5. 以降は**毎朝日本時間6:00に自動実行**されます。

### 【ステップ7】iPhoneのホーム画面に追加（PWA化）
1. iPhoneの **Safari** で、発行されたGitHub PagesのURLを開く。
2. 画面下部の中央にある **共有ボタン**（四角から上向き矢印が出ているアイコン）をタップ。
3. メニューを少し下にスクロールし、**「ホーム画面に追加」** をタップ。
4. 右上の **「追加」** をタップ。
5. ホーム画面に可愛いピンクの雪の結晶アイコンが追加され、タップするとアプリとして全画面で開くようになります！

---

## ⚙️ 自分好みにカスタマイズする方法

`scripts/config.json` を編集してコミットするだけで自由に調整できます。

- **NGワードの追加**: `"ng_keywords"` 配列に除外したい言葉を追加。
- **表示件数の調整**: `"max_items_sakuma": 5`, `"max_items_snowman": 5` をお好みの件数に変更。
- **対象期間**: `"lookback_hours": 36`（直近何時間以内の記事を拾うか）。

