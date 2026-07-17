# Filmoteca

Jednoduchá, ale už prakticky použitelná desktopová aplikace pro vlastní databázi filmů a seriálů. Data zůstávají lokálně v SQLite databázi. Žádný účet, reklamy ani předplatné, protože i databáze oblíbených filmů se dnes jinak pokouší stát sociální sítí.

## Co umí první verze

- filmy i seriály,
- hodnocení 0–5 hvězd,
- oblíbené položky a stav „chci vidět / sleduji / zhlédnuto“,
- rok, žánry, země, původní název, poznámky a plakát,
- libovolný počet video souborů u jedné položky,
- automatické načtení technických údajů přes `ffprobe`,
- rozlišení, video kodek, FPS, délka, datový tok a velikost,
- seznam zvukových stop: jazyk, kodek, kanály, vzorkování a datový tok,
- seznam titulků: jazyk, formát, výchozí a vynucené titulky,
- hledání a filtry Film / Seriál / Oblíbené,
- otevření video souboru ve výchozím přehrávači,
- opakovaná analýza souboru po jeho změně.

## Instalace na Linuxu

```bash
sudo apt install python3 python3-venv ffmpeg
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Instalace na Windows

1. Nainstaluj Python 3.11 nebo novější.
2. Nainstaluj FFmpeg a přidej jeho složku `bin` do proměnné `PATH`.
3. V PowerShellu v adresáři projektu spusť:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py main.py
```

## Uložení dat

Aplikace používá systémový adresář aplikace:

- Linux obvykle `~/.local/share/Fousliez/Filmoteca/`,
- Windows obvykle `%APPDATA%\Fousliez\Filmoteca\`.

Uvnitř je databáze `filmoteca.sqlite3` a kopie vybraných plakátů. Video soubory se nekopírují a při odebrání z databáze se z disku nemažou.

## Vývoj a testy

```bash
pytest
python -m compileall filmoteca main.py
```

## Záměrná omezení první verze

- seriál je jedna položka s více soubory; samostatný katalog řad a epizod přijde později,
- metadata z internetu se zatím nestahují,
- čísla řad a epizod se zkoušejí načíst z názvu souboru a lze je ručně upravit,
- automatická tvorba instalačních balíčků pro Windows a Linux zatím není zapojená.
