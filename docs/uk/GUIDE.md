# Quorvane: Посібник із встановлення

Цей посібник показує, як запустити Quorvane на власному комп'ютері або на VPS. Це займе близько 15 хвилин.

> Бета: Quorvane і його панель керування перебувають у стадії бети. Їх не було ретельно протестовано, особливо на великих серверах і в усіх ситуаціях Discord. Можливі помилки, робіть резервні копії папки data та повідомляйте про проблеми. Використання на власний ризик.

<!-- toc -->

- [Створення Discord-бота](#створення-discord-бота)
- [Запуск на власному комп'ютері](#запуск-на-власному-компютері)
  - [Windows (PowerShell)](#windows-powershell)
  - [Linux і macOS](#linux-і-macos)
- [Запуск на VPS](#запуск-на-vps)
- [Запуск через Docker](#запуск-через-docker)
- [Перші кроки в Discord](#перші-кроки-в-discord)
- [Структура, команда та огляд (1.5)](#структура-команда-та-огляд-15)
- [Оновлення та резервні копії](#оновлення-та-резервні-копії)
- [Музика (необов'язково)](#музика-необовязково)
- [Необов'язково: читання зображень і мови](#необовязково-читання-зображень-і-мови)
- [Панель керування](#панель-керування)
- [Скіли, ШІ та профіль бота (необов'язково)](#скіли-ші-та-профіль-бота-необовязково)
- [Нове в 1.12: скляна панель, протоколи, скам-посилання](#нове-в-112-скляна-панель-протоколи-скам-посилання)
- [Усунення несправностей](#усунення-несправностей)
- [Підтримка](#підтримка)

<!-- tocstop -->

## Створення Discord-бота

1. Відкрийте [Discord Developer Portal](https://discord.com/developers/applications) і натисніть New Application.
2. Відкрийте вкладку Bot і натисніть Reset Token. Скопіюйте токен і тримайте його в таємниці.
3. На тій самій вкладці увімкніть Server Members Intent і Message Content Intent.
4. Відкрийте OAuth2, URL Generator. Виберіть scopes bot і applications.commands.
5. Виберіть права: Manage Roles, Manage Channels, Kick Members, Ban Members, Moderate Members, View Audit Log, Manage Messages, Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions, Move Members. Administrator теж підходить і є найпростішим варіантом.
6. Відкрийте створене посилання та додайте бота на свій сервер.
7. У налаштуваннях сервера перемістіть роль бота на самий верх списку ролей. Бот може керувати лише ролями, що розташовані нижче за його власну.

Також можна скористатися цим посиланням-запрошенням. Замініть YOUR_CLIENT_ID на Application ID із Developer Portal:

```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot+applications.commands&permissions=1099797228758
```

## Запуск на власному комп'ютері

Встановіть Python 3.11 або новіший і Git, потім виконайте ці команди в терміналі.

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

### Linux і macOS

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

Відкрийте файл .env і замініть зразок токеном вашого бота. Бот буде в мережі, щойно в консолі з'явиться рядок, що починається з online as. Не закривайте вікно: бот зупиняється разом із ним.

## Запуск на VPS

Ці команди підходять для Ubuntu та Debian і налаштовують бота як службу з автозапуском.

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

Стан перевіряється командою systemctl status quorvane. Коли бот готовий, у журналі з'являється рядок, що починається з online as.

## Запуск через Docker

Docker необов'язковий. Спершу створіть файл .env, потім виконайте:

```bash
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml logs -f
```

## Перші кроки в Discord

Використовуйте ці команди на своєму сервері та замініть назви каналів своїми.

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

Усі функції описано в довіднику команд: [COMMANDS.md](../COMMANDS.md).

## Структура, команда та огляд (1.5)

Ці кроки налаштовують нові функції. Кожну можна вимкнути через /admin module, а префікс і тексти залишаються налаштовуваними для кожного сервера.

1. Подивитися, що налаштовано: `/admin module overview` показує кожен модуль зі станом і статусом налаштування. Панель керування показує те саме в розділі налаштування.
2. Знайти команду: `/info find text:ban` шукає за словом серед усіх команд, `/help` показує групи.
3. Опублікувати правила з кнопкою прийняття: `/structure rules setup`, потім `/structure rules add`, потім `/structure rules post`. Тим, хто не прийняв нову версію, нагадують кожні кілька годин.
4. Вказати боту, хто входить до команди: `/team duty roster`. Це використовують списки доступних працівників і маршрутизація тікетів та сповіщень.
5. Навести лад у неактивних каналах: `/structure archive setup`, потім `/structure archive scan`.
6. Повертати ролі учасникам, що повернулися: `/members stickyroles setup`.
7. Стежити за читабельністю імен: `/members nickname setup`, перед `/members nickname scan` перевірте через `/members nickname check`.
8. Перед великими змінами експортуйте налаштування через `/admin config export` і перевірте ролі та канали через `/server diagnose`.

## Оновлення та резервні копії

Оновлення бота:

```bash
cd /opt/quorvane
sudo -u quorvane git pull
sudo .venv/bin/pip install -r requirements.txt
sudo systemctl restart quorvane
```

Збережіть налаштування, скопіювавши папку data, наприклад:

```bash
tar czf quorvane-data-$(date +%F).tar.gz data
```

## Музика (необов'язково)

Для модуля музики потрібен ffmpeg на комп'ютері, де працює бот. Покладіть свою музику в папку music/ як Виконавець/Альбом/01 - Назва.flac або дозвольте завантаження. Папка може стати великою, тому тримайте її на диску з місцем або в томі Docker.

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

Quorvane Music: щоб музика працювала на окремому боті, який може цілодобово залишатися в голосовому каналі, створіть другий застосунок у Discord Developer Portal, запишіть його токен у .env як MUSIC_TOKEN і встановіть music_bot.enabled у true в settings.json. Після перезапуску сторінка «Музика» в панелі покаже кнопку, що додає Quorvane Music на сервер. Посилання Spotify, Apple Music і Tidal відтворюються через YouTube або SoundCloud; для альбомів і плейлистів Tidal також потрібні TIDAL_CLIENT_ID і TIDAL_CLIENT_SECRET у .env. Використовуйте на власний ризик, див. розділ «Музика» в README.

## Необов'язково: читання зображень і мови

Щоб модуль захисту від шахрайства читав текст на зображеннях, встановіть tesseract на комп'ютері, де працює бот (в образі Docker він уже є). Потім перевірте командою /security antiscam status, що він готовий. Мову повідомлень, які бачать учасники, обирають командою /admin language.

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

## Панель керування

Панель керування — це вебсторінка, що працює всередині бота. Після входу через Discord ви змінюєте налаштування своїх серверів перемикачами, меню та полями замість команд: модулі, канали, ролі, порогові значення, тексти, префікс і мова. Вона також показує останні справи модерації, експортує та імпортує налаштування. Вона однаково працює на вашому комп'ютері та на VPS і вимкнена, доки ви її не ввімкнете.

1. Відкрийте свій застосунок у Developer Portal, перейдіть до OAuth2 і скопіюйте Client Secret у файл .env.
2. На тій самій сторінці додайте адресу перенаправлення http://localhost:8080/callback.
3. Увімкніть панель у settings.json.
4. Перезапустіть бота та відкрийте http://localhost:8080 у браузері. Увійдіть через Discord.

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

Залиште host рівним 127.0.0.1 і виберіть один із двох шляхів. Перший — SSH-тунель: назовні нічого не відкривається, а http://localhost:8080 ви відкриваєте на своєму комп'ютері, поки працює тунель.

```bash
ssh -L 8080:127.0.0.1:8080 user@your-server
```

Другий — HTTPS через зворотний проксі, наприклад Caddy, який сам отримує сертифікат (див. deploy/Caddyfile.example). Потім вкажіть у public_url свою https-адресу, додайте https://ваша-адреса/callback як перенаправлення в Developer Portal і встановіть trust_proxy у true:

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

## Скіли, ШІ та профіль бота (необов'язково)

Скілам потрібен лише бот: почни з `/support skill create`. Для ШІ потрібні обліковий запис і ключ API в Anthropic, OpenAI або Kimi (Moonshot); виконай `/support ai setup` і встав ключ у приватне вікно. Зберігай файл `data/ai.secret` разом із резервними копіями. Ім'я, картинку й банер бота можна змінювати в панелі в розділі «Профіль бота»; щоб змінювати їх усюди, додай свій Discord ID в `owner_ids` у `settings.json` (або будь власником застосунку). Подробиці — у README, розділ «Скіли та ШІ».

## Нове в 1.12: скляна панель, протоколи, скам-посилання

Панель використовує скляний дизайн, що відповідає світлій або темній темі пристрою: плаваюча верхня смуга, вузька смуга значків, яка розкривається в повне меню, та основна панель. У розділі «Налаштування», «Вигляд панелі» оберіть шаблон скла (Прозоре, Матове, Щільне) або налаштуйте розмиття, непрозорість, насиченість, підсвітку країв і відтінок.

Закриті тікети та мод-пошта зберігаються одним HTML-файлом, який відкривається в будь-якому браузері без інтернету. Копія для команди в каналі журналу містить нотатки з `/support ticket note`; копія для учасника — ніколи. `/support ticket close` приймає необов'язкову причину.

Анти-скам спершу перевіряє посилання: посилання, що підробляють Discord або Steam, та посилання IP-логерів (Grabify, IPLogger та інші) видаляються одразу. Дія за замовчуванням тепер гулаг; сервери, де вже збережено іншу дію, зберігають її, доки ви не зміните. Копії, які той самий учасник опублікував в інших каналах за три хвилини, теж видаляються.

Сторінка «Журнали» в панелі показує те, що бот пише в канали журналу: повідомлення, учасники, модерація, безпека, голос і сервер, з пошуком, фільтром за видом і переглядом наживо. Читати її можуть модератори та вище. Записи зберігаються 30 днів у `data/logbook.db` (налаштування журналу) і видаляються командами приватності. З ключем ШІ команда може запитувати бота звичайними словами: згадати його на початку повідомлення або використати `/support ai ask`, наприклад «як справи на сервері?». Асистент лише читає, через фіксовані інструменти (стан, модулі, випадки, безпека, тікети, активність, журнали), і кожне запитання з'являється в журналах разом із використаними інструментами.

**Нове у 2.0**

- Скляна панель із перемикачем світлої й темної теми, сторінка «Журнали» з переглядом наживо, пошуком, фільтром за датою та експортом CSV, сторінка «Учасники», збережені протоколи тікетів і редаговані випадки.
- Асистент: команда запитує звичайними словами в Discord або в панелі. Він відповідає за допомогою інструментів лише для читання, може читати Railway, репозиторій GitHub і веб-адреси, якщо ви їх підключите, і виконує дію лише після підтвердження кнопкою.
- Анти-скам одразу видаляє підроблені посилання Discord і Steam, посилання IP-логерів, QR-коди, що на них ведуть, і скам-зображення, надіслані посиланням. Дія за замовчуванням — гулаг, копії в інших каналах видаляються, а сервери вашого бота можуть ділити список спійманих акаунтів.
- Інструменти каналів: гілка під кожним повідомленням, канали лише для зображень і посилань, автоматична публікація оголошень і `/structure solved` для дописів форуму.
- Вітальне зображення, рейтинг часу в голосових каналах `/info voicetop` і переклад через `/support translate` або правий клік.
- API лише для читання з токеном, щоб інші програми читали числа та журнали сервера.

## Усунення несправностей

- Слеш-команди не з'являються: зачекайте кілька хвилин, перезапустіть Discord і переконайтеся, що бота запрошено зі scope applications.commands.
- Бот зупиняється з помилкою привілейованих інтентів: увімкніть Server Members Intent і Message Content Intent у Developer Portal.
- Improper token: скопіюйте токен знову й переконайтеся, що в .env записано саме DISCORD_TOKEN=токен, без пробілів і лапок.
- I cannot assign that role: розмістіть роль бота вище за роль, якою він має керувати.
- Нічого не журналюється: задайте канал командою /server log set і переконайтеся, що бот може в ньому надсилати повідомлення, вбудовувати посилання та прикріплювати файли.
- Unknown timezone: виконайте pip install tzdata і перезапустіть бота.
- Щось не працює без видимої причини: помилки та попередження виводяться в консоль. На VPS читайте їх командою journalctl -u quorvane -f.

## Підтримка

Помилки, ідеї та пропозиції: Discord @justyyin або issue на GitHub.

Copyright (c) Justyn - made in Germany
