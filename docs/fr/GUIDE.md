# Quorvane: Guide d'installation

Ce guide explique comment faire fonctionner Quorvane sur votre ordinateur ou sur un VPS. Comptez environ 15 minutes.

> Bêta : Quorvane et son tableau de bord sont en phase bêta. Ils n'ont pas été testés à fond, surtout pas sur de grands serveurs ni face à toutes les situations de Discord. Attendez-vous à des bugs, sauvegardez le dossier data et signalez les problèmes. Utilisation à vos risques.

<!-- toc -->

- [Créer le bot Discord](#créer-le-bot-discord)
- [Exécuter sur votre ordinateur](#exécuter-sur-votre-ordinateur)
  - [Windows (PowerShell)](#windows-powershell)
  - [Linux et macOS](#linux-et-macos)
- [Exécuter sur un VPS](#exécuter-sur-un-vps)
- [Exécuter avec Docker](#exécuter-avec-docker)
- [Premiers pas sur Discord](#premiers-pas-sur-discord)
- [Structure, équipe et vue d'ensemble (1.5)](#structure-équipe-et-vue-densemble-15)
- [Mises à jour et sauvegardes](#mises-à-jour-et-sauvegardes)
- [Musique (facultatif)](#musique-facultatif)
- [Facultatif : lire les images et les langues](#facultatif--lire-les-images-et-les-langues)
- [Tableau de bord](#tableau-de-bord)
- [Skills, IA et profil du bot (facultatif)](#skills-ia-et-profil-du-bot-facultatif)
- [Nouveau dans la 1.12 : tableau de bord en verre, transcriptions, liens d'arnaque](#nouveau-dans-la-112--tableau-de-bord-en-verre-transcriptions-liens-darnaque)
- [Dépannage](#dépannage)
- [Assistance](#assistance)

<!-- tocstop -->

## Créer le bot Discord

1. Ouvrez le [Discord Developer Portal](https://discord.com/developers/applications) et cliquez sur New Application.
2. Ouvrez l'onglet Bot et cliquez sur Reset Token. Copiez le jeton et gardez-le secret.
3. Sur le même onglet, activez Server Members Intent et Message Content Intent.
4. Ouvrez OAuth2, URL Generator. Sélectionnez les scopes bot et applications.commands.
5. Sélectionnez les permissions : Manage Roles, Manage Channels, Kick Members, Ban Members, Moderate Members, View Audit Log, Manage Messages, Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions, Move Members. Administrator fonctionne aussi et reste le choix le plus simple.
6. Ouvrez l'URL générée et ajoutez le bot à votre serveur.
7. Dans les paramètres du serveur, placez le rôle du bot tout en haut de la liste des rôles. Le bot ne peut gérer que les rôles situés sous son propre rôle.

Vous pouvez aussi utiliser cette URL d'invitation. Remplacez YOUR_CLIENT_ID par l'Application ID du Developer Portal :

```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot+applications.commands&permissions=1099797228758
```

## Exécuter sur votre ordinateur

Installez Python 3.11 ou plus récent et Git, puis exécutez ces commandes dans un terminal.

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

### Linux et macOS

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

Ouvrez le fichier .env et remplacez l'exemple par le jeton de votre bot. Le bot est en ligne dès que la console affiche la ligne commençant par online as. Laissez la fenêtre ouverte, le bot s'arrête quand vous la fermez.

## Exécuter sur un VPS

Ces commandes concernent Ubuntu ou Debian et installent le bot comme service qui démarre automatiquement.

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

Vérifiez l'état avec systemctl status quorvane. Le journal affiche la ligne commençant par online as quand le bot est prêt.

## Exécuter avec Docker

Docker est facultatif. Créez d'abord le fichier .env, puis lancez :

```bash
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml logs -f
```

## Premiers pas sur Discord

Utilisez ces commandes sur votre serveur et remplacez les noms de salons par les vôtres.

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

Toutes les fonctions sont décrites dans la référence des commandes : [COMMANDS.md](../COMMANDS.md).

## Structure, équipe et vue d'ensemble (1.5)

Ces étapes configurent les fonctions plus récentes. Chacune peut être désactivée avec /admin module, et le préfixe et les textes restent modifiables par serveur.

1. Voir ce qui est configuré : `/admin module overview` liste chaque module avec son état et s'il est configuré. Le tableau de bord affiche la même chose dans son panneau de configuration.
2. Trouver une commande : `/info find text:ban` cherche dans toutes les commandes par mot, `/help` affiche les groupes.
3. Publier les règles avec un bouton d'acceptation : `/structure rules setup`, puis `/structure rules add`, puis `/structure rules post`. Les membres qui n'ont pas accepté une nouvelle version sont relancés toutes les quelques heures.
4. Indiquer au bot qui fait partie de l'équipe : `/team duty roster`. Les listes du personnel disponible et le routage des tickets et alertes l'utilisent.
5. Ranger les salons inactifs : `/structure archive setup`, puis `/structure archive scan`.
6. Rendre leurs rôles aux membres qui reviennent : `/members stickyroles setup`.
7. Garder des noms lisibles : `/members nickname setup`, tester avec `/members nickname check` avant `/members nickname scan`.
8. Avant de gros changements, exportez les réglages avec `/admin config export` et vérifiez rôles et salons avec `/server diagnose`.

## Mises à jour et sauvegardes

Mettre le bot à jour :

```bash
cd /opt/quorvane
sudo -u quorvane git pull
sudo .venv/bin/pip install -r requirements.txt
sudo systemctl restart quorvane
```

Sauvegardez vos réglages en copiant le dossier data, par exemple :

```bash
tar czf quorvane-data-$(date +%F).tar.gz data
```

## Musique (facultatif)

Le module musique nécessite ffmpeg sur l'ordinateur qui exécute le bot. Placez votre musique dans le dossier music/ sous la forme Artiste/Album/01 - Titre.flac, ou autorisez les téléchargements. Le dossier peut devenir volumineux : gardez-le sur un disque avec de la place ou dans un volume Docker.

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

Quorvane Music : pour faire tourner la musique sur un bot à part qui peut rester dans un salon vocal 24 heures sur 24, crée une seconde application dans le Discord Developer Portal, écris son token dans .env sous MUSIC_TOKEN et mets music_bot.enabled à true dans settings.json. Après un redémarrage, la page Musique du tableau de bord affiche un bouton qui ajoute Quorvane Music au serveur. Les liens Spotify, Apple Music et Tidal sont lus via YouTube ou SoundCloud ; les albums et playlists Tidal demandent aussi TIDAL_CLIENT_ID et TIDAL_CLIENT_SECRET dans .env. Utilisation à tes propres risques, voir la section Musique du README.

## Facultatif : lire les images et les langues

Pour que le module anti-arnaque lise le texte des images, installez tesseract sur l'ordinateur qui exécute le bot (l'image Docker le contient déjà). Vérifiez ensuite avec /security antiscam status qu'il est prêt. Choisissez la langue des messages que voient les membres avec /admin language.

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

## Tableau de bord

Le tableau de bord est une page web qui s'exécute dans le bot. Après connexion avec Discord, vous modifiez les réglages de vos serveurs avec des interrupteurs, des menus et des champs au lieu de commandes : modules, salons, rôles, seuils, textes, préfixe et langue. Il affiche aussi les derniers cas de modération et exporte et importe les réglages. Il fonctionne de la même façon sur votre ordinateur et sur un VPS, et reste désactivé tant que vous ne l'activez pas.

1. Ouvrez votre application dans le Developer Portal, allez dans OAuth2 et copiez le Client Secret dans le fichier .env.
2. Sur la même page, ajoutez l'adresse de redirection http://localhost:8080/callback.
3. Activez le tableau de bord dans settings.json.
4. Redémarrez le bot et ouvrez http://localhost:8080 dans votre navigateur. Connectez-vous avec Discord.

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

Laissez host sur 127.0.0.1 et choisissez l'une des deux méthodes. D'abord un tunnel SSH : rien n'est exposé, vous ouvrez http://localhost:8080 sur votre ordinateur tant que le tunnel est actif.

```bash
ssh -L 8080:127.0.0.1:8080 user@your-server
```

Ensuite HTTPS via un reverse proxy comme Caddy, qui obtient seul un certificat (voir deploy/Caddyfile.example). Réglez alors public_url sur votre adresse https, ajoutez https://votre-adresse/callback comme redirection dans le Developer Portal et mettez trust_proxy sur true :

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

## Skills, IA et profil du bot (facultatif)

Les skills n'ont besoin que du bot : commence avec `/support skill create`. Pour l'IA, il te faut un compte et une clé API chez Anthropic, OpenAI ou Kimi (Moonshot) ; lance `/support ai setup` et colle la clé dans la boîte privée. Conserve le fichier `data/ai.secret` avec tes sauvegardes. Le nom, l'image et la bannière du bot se changent dans le tableau de bord sous Profil du bot ; pour les changer partout, ajoute ton ID Discord dans `owner_ids` de `settings.json` (ou sois le propriétaire de l'application). Les détails sont dans le README, section Skills et IA.

## Nouveau dans la 1.12 : tableau de bord en verre, transcriptions, liens d'arnaque

Le tableau de bord utilise un design en verre qui suit le réglage clair ou sombre de votre appareil : une barre supérieure flottante, une étroite barre d'icônes qui s'ouvre en menu complet, et un panneau principal. Dans Paramètres, Apparence du tableau de bord, choisissez un préréglage (Clair, Dépoli, Opaque) ou réglez vous-même le flou, l'opacité, la saturation, la lumière des bords et la teinte.

Les tickets et le mod-mail fermés sont enregistrés dans un seul fichier HTML qui s'ouvre dans n'importe quel navigateur, sans internet. La copie de l'équipe dans le salon de logs contient les notes écrites avec `/support ticket note` ; la copie du membre jamais. `/support ticket close` accepte une raison facultative.

L'anti-arnaque vérifie d'abord les liens : ceux qui imitent Discord ou Steam et les liens IP logger (Grabify, IPLogger et autres) sont supprimés immédiatement. L'action par défaut est désormais le goulag ; les serveurs qui ont déjà enregistré une autre action la gardent jusqu'à ce que vous la changiez. Les copies publiées par le même membre dans d'autres salons en trois minutes sont aussi supprimées.

La page Journaux du tableau de bord montre ce que le bot écrit dans les salons de logs : messages, membres, modération, sécurité, vocal et serveur, avec recherche, filtre par type et vue en direct. Les modérateurs et au-dessus peuvent la lire. Les entrées sont conservées 30 jours dans `data/logbook.db` (options de logs) et supprimées avec les commandes de confidentialité. Avec une clé d'IA, l'équipe peut interroger le bot en langage courant : le mentionner au début d'un message ou utiliser `/support ai ask`, par exemple « comment va le serveur ? ». L'assistant ne fait que lire, via des outils fixes (état, modules, cas, sécurité, tickets, activité, journaux), et chaque question apparaît dans les journaux avec les outils utilisés.

**Nouveau dans la 2.0**

- Tableau de bord en verre avec un bouton clair/sombre, une page Journaux avec vue en direct, recherche, filtre par date et export CSV, une page Membres, les transcriptions de tickets conservées et des cas modifiables.
- Assistant : l'équipe pose ses questions en langage courant dans Discord ou dans le tableau de bord. Il répond avec des outils en lecture seule, peut lire Railway, un dépôt GitHub et des adresses web si vous les connectez, et n'exécute une action qu'après confirmation par un bouton.
- L'anti-arnaque supprime immédiatement les faux liens Discord et Steam, les liens IP logger, les codes QR qui y mènent et les images d'arnaque publiées sous forme de lien. L'action par défaut est le goulag, les copies dans d'autres salons sont supprimées et les serveurs de votre bot peuvent partager une liste de comptes pris.
- Outils de salon : un fil sous chaque message, des salons réservés aux images et aux liens, la publication automatique des annonces et `/structure solved` pour les posts de forum.
- Image de bienvenue, classement du temps en vocal avec `/info voicetop` et traduction avec `/support translate` ou par clic droit.
- Une API en lecture seule avec un jeton, pour que d'autres programmes lisent les chiffres et les journaux d'un serveur.

## Dépannage

- Les commandes slash n'apparaissent pas : attendez quelques minutes, redémarrez Discord et vérifiez que le bot a été invité avec le scope applications.commands.
- Le bot s'arrête avec une erreur d'intents privilégiés : activez Server Members Intent et Message Content Intent dans le Developer Portal.
- Improper token : copiez à nouveau le jeton et vérifiez que .env contient exactement DISCORD_TOKEN=jeton, sans espace ni guillemets.
- I cannot assign that role : placez le rôle du bot au-dessus du rôle qu'il doit gérer.
- Rien n'est journalisé : définissez un salon avec /server log set et vérifiez que le bot peut y envoyer des messages, intégrer des liens et joindre des fichiers.
- Unknown timezone : exécutez pip install tzdata et redémarrez le bot.
- Quelque chose échoue sans raison visible : les erreurs et avertissements sont écrits dans la console. Sur un VPS, lisez-les avec journalctl -u quorvane -f.

## Assistance

Bugs, idées et suggestions : Discord @justyyin ou une issue GitHub.

Copyright (c) Justyn - made in Germany
