# Quorvane: セットアップガイド

このガイドでは、自分のコンピューターまたは VPS で Quorvane を動かす方法を説明します。所要時間は約 15 分です。

> ベータ版：Quorvane とそのダッシュボードはベータ段階です。十分にテストされておらず、特に大規模なサーバーや Discord のあらゆる状況では確認していません。不具合が起こりうるため、data フォルダーのバックアップを取り、問題を報告してください。自己責任でご利用ください。

<!-- toc -->

- [Discord ボットを作成する](#discord-ボットを作成する)
- [自分のコンピューターで動かす](#自分のコンピューターで動かす)
  - [Windows (PowerShell)](#windows-powershell)
  - [Linux と macOS](#linux-と-macos)
- [VPS で動かす](#vps-で動かす)
- [Docker で動かす](#docker-で動かす)
- [Discord での最初の手順](#discord-での最初の手順)
- [構成・チーム・概要(1.5)](#構成チーム概要15)
- [更新とバックアップ](#更新とバックアップ)
- [音楽（任意）](#音楽任意)
- [任意：画像の読み取りと言語](#任意画像の読み取りと言語)
- [ダッシュボード](#ダッシュボード)
- [スキル、AI、ボットのプロフィール（任意）](#スキルaiボットのプロフィール任意)
- [1.12 の新機能：ガラス風ダッシュボード、記録ファイル、詐欺リンク](#112-の新機能ガラス風ダッシュボード記録ファイル詐欺リンク)
- [トラブルシューティング](#トラブルシューティング)
- [サポート](#サポート)

<!-- tocstop -->

## Discord ボットを作成する

1. [Discord Developer Portal](https://discord.com/developers/applications) を開き、New Application をクリックします。
2. Bot タブを開き、Reset Token をクリックします。トークンをコピーし、他人に見せないでください。
3. 同じタブで Server Members Intent と Message Content Intent をオンにします。
4. OAuth2 の URL Generator を開き、スコープ bot と applications.commands を選びます。
5. 権限を選びます：Manage Roles、Manage Channels、Kick Members、Ban Members、Moderate Members、View Audit Log、Manage Messages、Send Messages、Embed Links、Attach Files、Read Message History、Add Reactions、Move Members。Administrator でも動作し、これが最も簡単です。
6. 生成された URL を開き、ボットをサーバーに追加します。
7. サーバー設定で、ボットのロールをロール一覧の一番上に移動します。ボットは自分のロールより下にあるロールしか管理できません。

次の招待 URL も使えます。YOUR_CLIENT_ID は Developer Portal の Application ID に置き換えてください：

```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot+applications.commands&permissions=1099797228758
```

## 自分のコンピューターで動かす

Python 3.11 以降と Git をインストールし、ターミナルで次のコマンドを実行します。

### Windows (PowerShell)

```powershell
git clone https://github.com/Justyyin/Quorvane-2.0.git
cd quorvane
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env
python main.py
```

### Linux と macOS

```bash
git clone https://github.com/Justyyin/Quorvane-2.0.git
cd quorvane
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python main.py
```

.env ファイルを開き、プレースホルダーをボットのトークンに置き換えます。コンソールに online as で始まる行が表示されれば、ボットはオンラインです。ウィンドウを閉じるとボットも止まるので、開いたままにしてください。

## VPS で動かす

次のコマンドは Ubuntu または Debian 用で、ボットを自動起動するサービスとして設定します。

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git ffmpeg libopus0 ffmpeg libopus0 ffmpeg libopus0 ffmpeg libopus0 ffmpeg libopus0 ffmpeg libopus0
sudo git clone https://github.com/Justyyin/Quorvane-2.0.git /opt/quorvane
sudo useradd --system --no-create-home --shell /usr/sbin/nologin quorvane
cd /opt/quorvane
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
sudo cp .env.example .env
sudo nano .env
sudo mkdir -p data
sudo chown -R quorvane:quorvane /opt/quorvane
sudo chmod 600 .env
sudo cp deploy/quorvane.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now quorvane
sudo journalctl -u quorvane -f
```

状態は systemctl status quorvane で確認します。準備ができると、ログに online as で始まる行が表示されます。

## Docker で動かす

Docker は任意です。先に .env ファイルを作成し、次を実行します。

```bash
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml logs -f
```

## Discord での最初の手順

サーバーで次のコマンドを使い、チャンネル名を自分のものに置き換えてください。

```
/server log set category:main channel:#logs
/access jailsetup setup
/automod toggle rule:phishing enabled:True action:jail
/automod toggle rule:words enabled:True
/automod add name:words value:example
/security raid setup enabled:True joins:5 seconds:10 action:timeout min_age_days:3
/security antinuke setup enabled:True action:strip
/access verify setup channel:#verify mode:captcha timeout_minutes:30
/community welcome set channel:#welcome message:Welcome {user} to {server}!
/server backup schedule enabled:True interval_hours:24 keep:7
/xp config enabled:True
/admin module list
```

すべての機能はコマンドリファレンスで説明しています： [COMMANDS.md](../COMMANDS.md).

## 構成・チーム・概要(1.5)

これらの手順で新しい機能を設定します。どの機能も /admin module でオフにでき、プレフィックスとテキストはサーバーごとに変更できます。

1. 設定状況を見る:`/admin module overview` は各モジュールの状態と設定済みかどうかを一覧表示します。ダッシュボードのセットアップパネルにも同じ内容が出ます。
2. コマンドを探す:`/info find text:ban` は単語ですべてのコマンドを検索し、`/help` はグループを表示します。
3. 同意ボタン付きでルールを公開する:`/structure rules setup`、`/structure rules add`、`/structure rules post` の順に実行します。新しい版に同意していないメンバーには数時間おきにお知らせが届きます。
4. 誰がスタッフかをボットに伝える:`/team duty roster`。対応可能なスタッフの一覧や、チケットと警告の振り分けで使われます。
5. 使われていないチャンネルを整理する:`/structure archive setup` のあと `/structure archive scan`。
6. 戻ってきたメンバーにロールを返す:`/members stickyroles setup`。
7. 名前を読みやすく保つ:`/members nickname setup`。`/members nickname scan` の前に `/members nickname check` で試します。
8. 大きな変更の前に `/admin config export` で設定を書き出し、`/server diagnose` でロールとチャンネルを確認してください。

## 更新とバックアップ

ボットを更新する：

```bash
cd /opt/quorvane
sudo -u quorvane git pull
sudo .venv/bin/pip install -r requirements.txt
sudo systemctl restart quorvane
```

data フォルダーをコピーして設定をバックアップします。例：

```bash
tar czf quorvane-data-$(date +%F).tar.gz data
```

## 音楽（任意）

音楽モジュールには、ボットを動かすコンピューターに ffmpeg が必要です。自分の音楽を music/ フォルダに アーティスト/アルバム/01 - 曲名.flac の形で置くか、ダウンロードを許可してください。フォルダは大きくなることがあるため、空き容量のあるディスクか Docker ボリュームに置いてください。

```
# Windows
winget install Gyan.FFmpeg
# macOS
brew install ffmpeg
# Ubuntu or Debian
sudo apt install -y ffmpeg libopus0

# in Discord
/admin module enable name:music
/music settings allow_download:True
```

Quorvane Music: 24 時間ボイスチャンネルに留まれる専用ボットで音楽を動かすには、Discord Developer Portal で 2 つ目のアプリケーションを作成し、そのトークンを .env に MUSIC_TOKEN として書き込み、settings.json の music_bot.enabled を true にします。再起動後、ダッシュボードの「音楽」ページに Quorvane Music をサーバーに追加するボタンが表示されます。Spotify、Apple Music、Tidal のリンクは YouTube または SoundCloud で再生されます。Tidal のアルバムとプレイリストには .env の TIDAL_CLIENT_ID と TIDAL_CLIENT_SECRET も必要です。利用は自己責任です。README の「音楽」セクションを参照してください。

## 任意：画像の読み取りと言語

詐欺対策モジュールに画像内の文字を読ませるには、ボットを動かすコンピューターに tesseract をインストールします（Docker イメージには含まれています）。その後 /security antiscam status で準備できているか確認します。メンバーに表示されるメッセージの言語は /admin language で選びます。

```
# Ubuntu or Debian
sudo apt install -y tesseract-ocr
# macOS
brew install tesseract
# Windows
winget install UB-Mannheim.TesseractOCR

# in Discord
/security antiscam status
/admin language code:de
```

## ダッシュボード

ダッシュボードはボットの中で動くウェブページです。Discord でログインすると、コマンドの代わりにスイッチ、メニュー、入力欄でサーバーの設定を変更できます。対象はモジュール、チャンネル、ロール、しきい値、テキスト、プレフィックス、言語です。直近のモデレーションケースの表示や、設定のエクスポートとインポートもできます。自分のコンピューターでも VPS でも同じように動作し、オンにするまでは無効です。

1. Developer Portal でアプリケーションを開き、OAuth2 に進んで、Client Secret を .env ファイルにコピーします。
2. 同じページでリダイレクトアドレス http://localhost:8080/callback を追加します。
3. settings.json でダッシュボードをオンにします。
4. ボットを再起動し、ブラウザで http://localhost:8080 を開いて Discord でログインします。

```
DISCORD_TOKEN=your-bot-token
DISCORD_CLIENT_SECRET=your-oauth2-client-secret
```

```json
{
  "dashboard": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8080,
    "public_url": "http://localhost:8080"
  }
}
```

host は 127.0.0.1 のままにして、2 つの方法から選びます。1 つ目は SSH トンネルです。何も公開せず、トンネルが動いている間、自分のコンピューターで http://localhost:8080 を開きます。

```bash
ssh -L 8080:127.0.0.1:8080 user@your-server
```

2 つ目は Caddy のようなリバースプロキシを使った HTTPS です。証明書は自動で取得されます（deploy/Caddyfile.example を参照）。その場合は public_url を https アドレスにし、Developer Portal に https://あなたのアドレス/callback をリダイレクトとして追加し、trust_proxy を true にします：

```
dashboard.example.com {
	reverse_proxy 127.0.0.1:8080
}
```

```json
{
  "dashboard": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8080,
    "public_url": "https://dashboard.example.com",
    "trust_proxy": true
  }
}
```

## スキル、AI、ボットのプロフィール（任意）

スキルに必要なのはボットだけです。`/support skill create` から始めてください。AIには、Anthropic、OpenAI、Kimi（Moonshot）のアカウントとAPIキーが必要です。`/support ai setup` を実行し、非公開の入力欄にキーを貼り付けます。ファイル `data/ai.secret` はバックアップと一緒に保管してください。ボットの名前、画像、バナーはダッシュボードの「ボットのプロフィール」で変更できます。すべての場所で変更するには、あなたのDiscord IDを `settings.json` の `owner_ids` に追加してください（またはアプリケーションの所有者になってください）。詳細はREADMEの「スキルとAI」の項にあります。

## 1.12 の新機能：ガラス風ダッシュボード、記録ファイル、詐欺リンク

ダッシュボードは端末のライト／ダーク設定に従うガラスデザインです。浮かぶトップバー、フルメニューに開く細いアイコンレール、そして 1 つのメインパネルで構成されます。「設定」の「ダッシュボードの外観」で、ガラスのプリセット（クリア、すりガラス、ソリッド）を選ぶか、ぼかし、不透明度、彩度、縁のハイライト、色合いを自分で調整できます。

クローズしたチケットとモッドメールは、どのブラウザーでも開けてインターネット不要の 1 つの HTML ファイルとして保存されます。ログチャンネルのチーム用コピーには `/support ticket note` のメモが含まれますが、メンバー用コピーには含まれません。`/support ticket close` には任意で理由を指定できます。

詐欺対策は最初にリンクを確認します。Discord や Steam を装うリンクと IP ロガーのリンク（Grabify、IPLogger など）はすぐに削除されます。詐欺への既定の対応はグラーグになりました。すでに別の対応を保存しているサーバーは、変更するまでその設定のままです。同じメンバーが 3 分以内に他のチャンネルへ投稿したコピーも削除されます。

ダッシュボードの「ログ」ページには、ボットがログチャンネルに書き込む内容（メッセージ、メンバー、モデレーション、セキュリティ、ボイス、サーバー）が表示され、検索、種類ごとの絞り込み、ライブ表示ができます。モデレーター以上が閲覧できます。項目は `data/logbook.db` に 30 日間保存され（ログオプション）、プライバシーコマンドで削除されます。AI キーがあれば、スタッフは普通の言葉でボットに質問できます。メッセージの先頭でメンションするか、`/support ai ask` を使います（例：「サーバーの調子はどう？」）。アシスタントは決まったツール（状態、モジュール、ケース、セキュリティ、チケット、アクティビティ、ログ）で読み取るだけで、質問は使ったツールとともにログに表示されます。

**2.0 の新機能**

- ライト／ダーク切り替え付きのガラス風ダッシュボード、ライブ表示・検索・日付フィルター・CSV エクスポートを備えたログページ、メンバーページ、保存されるチケット記録、編集できるケース。
- アシスタント：スタッフが Discord またはダッシュボードで普通の言葉で質問します。読み取り専用のツールで答え、接続すれば Railway、GitHub リポジトリ、ウェブアドレスも読めます。操作はスタッフがボタンで確認した後にだけ実行されます。
- 詐欺対策は、Discord や Steam を装うリンク、IP ロガーのリンク、それらにつながる QR コード、リンクとして投稿された詐欺画像をすぐに削除します。既定の対応はグラーグで、他のチャンネルのコピーも削除され、同じボットのサーバー間で検出したアカウントのリストを共有できます。
- チャンネルツール：すべてのメッセージにスレッド、画像とリンク専用のチャンネル、アナウンスの自動公開、フォーラム投稿用の `/structure solved`。
- ウェルカム画像、`/info voicetop` によるボイス時間ランキング、`/support translate` または右クリックでの翻訳。
- トークン付きの読み取り専用 API。他のプログラムがサーバーの数値とログを読み取れます。

## トラブルシューティング

- スラッシュコマンドが表示されない：数分待ってから Discord を再起動し、ボットを applications.commands スコープ付きで招待したか確認してください。
- 特権 Intent のエラーでボットが停止する：Developer Portal で Server Members Intent と Message Content Intent をオンにしてください。
- Improper token：トークンをもう一度コピーし、.env の内容が DISCORD_TOKEN=トークン だけで、空白や引用符がないことを確認してください。
- I cannot assign that role：ボットのロールを、管理させたいロールより上に移動してください。
- 何も記録されない：/server log set でチャンネルを設定し、ボットがそのチャンネルでメッセージ送信、リンク埋め込み、ファイル添付をできるか確認してください。
- Unknown timezone：pip install tzdata を実行してボットを再起動してください。
- 原因が分からないまま失敗する場合：エラーと警告はコンソールに出力されます。VPS では journalctl -u quorvane -f で確認できます。

## サポート

バグ、アイデア、提案：Discord の @justyyin または GitHub の issue へ。

Copyright (c) Justyn - made in Germany
