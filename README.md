# 📈 Tourenplanimport Timo Tool

Dieses Projekt automatisiert den täglichen Import der neuesten Tourenplan-CSV-Datei von einem SMB-Netzlaufwerk in eine MySQL-Datenbank. Es nutzt eine virtuelle Python-Umgebung und wird täglich über einen Cronjob ausgeführt.

## 📂 Projektstruktur

```bash
/opt/timo_tool/
├── timo_tool_tourenplan.py       # Hauptskript
├── .env              # Umgebungsvariablen für DB und Pfade
├── venv/             # Virtuelle Umgebung
```

## 🧱 Einrichtung

### 1. Virtuelle Umgebung vorbereiten

```bash
cd /opt/timo_tool
python3 -m venv venv
source venv/bin/activate
pip install python-dotenv mysql-connector-python requests
```

### 2. CIFS für SMB-Zugriff installieren

```bash
sudo apt update
sudo apt install cifs-utils
```

### 3. SMB-Zugangsdaten sicher speichern

```bash
sudo nano /root/.smbcredentials
```

Inhalt:

```
username=DEIN_USER
password=DEIN_PASS
```

```bash
sudo chmod 600 /root/.smbcredentials
```

### 4. Automount über `/etc/fstab`

```bash
sudo nano /etc/fstab
```

```
//192.168.230.27/LogoMate_Transfer/LogoMate_Import/SAP_HEP_LIVE/logomate_tourplan_live /mnt/tourenplan_share cifs credentials=/root/.smbcredentials,iocharset=utf8,uid=1000,gid=1000,file_mode=0644,dir_mode=0755,nofail 0 0
```

```bash
sudo mount -a
```

### 5. Umgebungsvariablen konfigurieren

```bash
nano /opt/timo_tool/.env
```

Beispiel:

```
MYSQL_HOST=dedi848.your-server.de
MYSQL_PORT=3306
MYSQL_USER=xxxx
MYSQL_PASSWORD=xxxxx
MYSQL_DATABASE=xxxxx
LOCAL_PATH_TOURENPLAN=/mnt/tourenplan_share
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/AAA.../messages?key=...&token=...

```

## 💡 forecast.py

Importiert die neueste Datei und aktualisiert die Tabelle `lm_tourenplan`. Fügt jeder Zeile den aktuellen Timestamp hinzu. Danach werden die Wochentage als Text komma getrennt in
eine neue Tabelle `lm_tourenplan_aggregiert` geschrieben.
Speichere folgendes Skript unter `/opt/timo_tool/timo_tool_tourenplan.py` und stelle sicher, dass es ausführbar ist:

```bash
chmod +x /opt/timo_tool/timo_tool_tourenplan.py
```


## ▶️ Manuell ausführen

```bash
/opt/timo_tool/venv/bin/python /opt/timo_tool/timo_tool_tourenplan.py
```

## 🧩 Systemd-Service

Um das Skript regelmäßig oder beim Systemstart auszuführen, kann ein `systemd`-Service eingerichtet werden.

### 1. Service-Datei erstellen

```bash
sudo nano /etc/systemd/system/timo_tool_tourenplan.service
```

#### Inhalt:

```ini
[Unit]
Description=CSV Datei importieren und Daten umwandeln und wegschreiben
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/timo_tool/
ExecStart=/opt/timo_tool/venv/bin/python /opt/timo_tool/timo_tool_tourenplan.py
EnvironmentFile=/opt/timo_tool/.env
StandardOutput=append:/var/log/timo_tool_tourenplan.log
StandardError=append:/var/log/timo_tool_tourenplan.log

[Install]
WantedBy=multi-user.target
```

---

### 2. Service aktivieren und starten

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable timo_tool_tourenplan.service
sudo systemctl start timo_tool_tourenplan.service
```

---

### 3. Service prüfen

Status anzeigen:

```bash
sudo systemctl status timo_tool_tourenplan.service
```

Logs live ansehen:

```bash
journalctl -u timo_tool_tourenplan.service -f
```

---


## ⏰ Optional: systemd-Timer (statt Cronjob)

Du kannst einen systemd-Timer verwenden, um den Export regelmäßig auszuführen (z. B. täglich um 03:00 Uhr).

### 1. Timer-Datei erstellen

```bash
sudo nano /etc/systemd/system/timo_tool_tourenplan.timer
```

#### Inhalt:

```ini
[Unit]
Description=Timer für Tourenplan-Import um 7:00 Uhr täglich

[Timer]
OnCalendar=*-*-* 07:00:00
Persistent=true
Unit=timo_tool_tourenplan.service

[Install]
WantedBy=timers.target
```

---

### 2. Timer aktivieren und starten

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now timo_tool_tourenplan.timer

```

---

### 3. Timer prüfen

Liste aktiver Timer anzeigen:

```bash
systemctl list-timers
```

Status eines bestimmten Timers anzeigen:

```bash
systemctl status timo_tool_tourenplan.timer
```

Logs des Services anzeigen:

```bash
journalctl -u timo_tool_tourenplan.service
```
