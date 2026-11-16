"""Link checks of the anti-scam module: IP loggers and domains that imitate Discord or Steam. Pure functions, no Discord objects."""

import re
from typing import Iterable, Optional

from .detect import host_match

# Services that record the IP address of everyone who opens the link, and the cover domains they hand out
IPLOGGERS = (
    "grabify.link", "grabify.org", "iplogger.org", "iplogger.com", "iplogger.ru", "iplogger.co", "iplogger.info", "iplogger.cn",
    "2no.co", "yip.su", "iplis.ru", "ezstat.ru", "02ip.ru", "ipgrabber.ru", "ipgraber.ru", "ipgrab.org", "whatstheirip.com", "blasze.com", "blasze.tk",
    "ps3cfw.com", "bmwforum.co", "leancoding.co", "stopify.co", "freegiftcards.co", "joinmy.site", "curiouscat.club", "catsnthings.fun",
    "catsnthing.com", "crabrave.pw", "lovebird.guru", "trulove.guru", "dateing.club", "otherhalf.life", "shrekis.life", "datasig.io", "datauth.io",
    "headshot.monster", "gaming-at-my.best", "progaming.monster", "yourmy.monster", "screenshare.host", "imageshare.best", "screenshot.best",
    "gamingfun.me", "mypic.icu", "spottyfly.com", "fortnight.space", "fortnitechat.site", "youshouldclick.us", "quickmessage.us",
    "partpicker.shop", "sportshub.bar", "locations.quest",
)
# Domains loaded from the list the owner of the bot set in settings.json (iplogger_list_url)
EXTRA: set[str] = set()
DOMAIN = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}")


def parse_list(text: str, limit: int = 5000) -> set[str]:
    """Domains of a plain list, one per line. Comments, addresses and hosts-file prefixes are understood, the rest is dropped."""
    out: set[str] = set()
    for line in (text or "").splitlines():
        word = line.split("#", 1)[0].strip().lower()
        if not word:
            continue
        word = word.split()[-1].split("://")[-1].split("/")[0].lstrip("*.").lstrip("|")
        if DOMAIN.fullmatch(word) and not any(host_match(word, d) for d in OFFICIAL):
            out.add(word)
            if len(out) >= limit:
                break
    return out


OFFICIAL = (
    "discord.com", "discord.gg", "discordapp.com", "discordapp.net", "discord.media", "discordstatus.com", "discord.gift", "discord.new", "dis.gd",
    "discord.dev", "discord.store", "steampowered.com", "steamcommunity.com", "steamstatic.com", "steamusercontent.com", "s.team",
)
TARGETS = ("discord", "discordapp", "discordgift", "steamcommunity", "steampowered")
LURES = ("nitro", "gift", "airdrop", "claim", "free", "promo", "bonus", "verify", "login", "trade")


def distance(a: str, b: str, limit: int = 2) -> int:
    """The edit distance of two words, counting a swap of neighbours as one step. Stops early above the limit."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    before: list[int] = []
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        new = [i]
        for j, cb in enumerate(b, 1):
            best = min(row[j] + 1, new[j - 1] + 1, row[j - 1] + (ca != cb))
            if before and i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                best = min(best, before[j - 2] + 1)
            new.append(best)
        before, row = row, new
        if min(row) > limit:
            return limit + 1
    return row[-1]


def plain(label: str) -> str:
    """A label with the usual swapped characters put back, so disc0rd reads like discord."""
    return label.translate(str.maketrans("013457", "oleast")).replace("rn", "m").replace("vv", "w")


def logger_host(hosts: Iterable[str], extra: Iterable[str] = (), allow: Iterable[str] = ()) -> Optional[str]:
    """The first host that belongs to an IP logger, or None."""
    allowed = [d.lower() for d in allow]
    known = list(IPLOGGERS) + sorted(EXTRA) + [d.lower() for d in extra]
    for host in hosts:
        h = host.lower().rstrip(".")
        if any(host_match(h, d) for d in allowed):
            continue
        if any(host_match(h, d) for d in known):
            return h
    return None


def fake_host(hosts: Iterable[str], allow: Iterable[str] = ()) -> Optional[str]:
    """The first host that imitates Discord or Steam, or None. Official domains and allowed ones never count."""
    safe = list(OFFICIAL) + [d.lower() for d in allow]
    for host in hosts:
        h = host.lower().rstrip(".")
        if not h or re.fullmatch(r"[\d.]+", h) or any(host_match(h, d) for d in safe):
            continue
        labels = h.split(".")
        own = labels[-3] if len(labels) > 2 and labels[-2] in ("co", "com", "org", "net") else labels[-2] if len(labels) > 1 else ""
        whole = "".join(labels[:-1]).replace("-", "")
        # only the name the owner registered is compared, a sub domain such as discordpy.readthedocs.io proves nothing
        for word in [w for w in re.split(r"[-_]", own) if w] + [own.replace("-", "")]:
            for shown in {word, plain(word)}:
                for target in TARGETS:
                    steps = distance(shown, target)
                    if (steps == 0 and (shown != word or target != "discord")) or 0 < steps <= (1 if len(target) < 12 else 2):
                        return h
        # the real name with a lure next to it on a foreign domain: discord-nitro.example, steamcommunity.gift-claim.example
        if any(t in whole for t in ("discord", "steamcommunity", "steampowered")) and any(lure in h for lure in LURES):
            return h
    return None
