import os
import csv
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import mysql.connector
import requests

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starte Script ...")

load_dotenv()

LOCAL_PATH_TOURENPLAN = os.getenv("LOCAL_PATH_TOURENPLAN")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

## Funktionen ###################################################################################################################
def send_error_notification(message):
    webhook_url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
    if webhook_url:
        payload = {"text": f"❗ *Fehler beim lm_tourenplan-Skript*\n\n```{message}```"}
        try:
            response = requests.post(webhook_url, json=payload)
            if response.status_code != 200:
                print(f"Fehler beim Senden der Google Chat Nachricht: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Fehler beim Versenden der Benachrichtigung: {e}")
    else:
        print("GOOGLE_CHAT_WEBHOOK_URL ist nicht gesetzt.")

def get_latest_file():
    files = [f for f in os.listdir(LOCAL_PATH_TOURENPLAN) if f.lower().endswith('.csv')]
    if not files:
        raise FileNotFoundError("Keine CSV-Dateien im Verzeichnis gefunden.")

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(LOCAL_PATH_TOURENPLAN, f)))
    latest_file_path = os.path.join(LOCAL_PATH_TOURENPLAN, latest_file)
    print(f"Verwende neueste Datei: {latest_file} (geändert am {datetime.fromtimestamp(os.path.getmtime(latest_file_path))})")
    return latest_file_path

def import_tourenplan_csv_to_mysql(filepath):
    print(f"Lese Datei: {filepath}")

    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    cursor = connection.cursor()

    print("Leere Tabelle lm_tourenplan ...")
    cursor.execute("TRUNCATE TABLE lm_tourenplan")

    with open(filepath, mode='r', encoding='utf-8', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        header = next(reader)
        expected_header = ["STANDORTID", "ANLIEFERDATUM", "WOCHENTAG"]
        if header != expected_header:
            raise ValueError(f"CSV-Header stimmt nicht überein. Erwartet: {expected_header}, gefunden: {header}")
        print(f"Header: {header}")

        row_count = 0
        for row in reader:
            if len(row) != 3:
                print(f"Überspringe fehlerhafte Zeile: {row}")
                continue

            sql = """
                INSERT INTO lm_tourenplan (STANDORTID, ANLIEFERDATUM, WOCHENTAG)
                VALUES (%s, %s, %s)
            """
            cursor.execute(sql, row)
            row_count += 1

    connection.commit()
    cursor.close()
    connection.close()
    print(f"Import abgeschlossen. {row_count} Zeilen eingefügt.")

def aggregate_wochentage_and_insert():
    print("Starte Aggregation von Wochentagen pro Standort ...")

    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    cursor = connection.cursor()

    # Ziel-Tabelle vorbereiten
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lm_tourenplan_aggregiert (
            STANDORTID VARCHAR(4) NOT NULL,
            WOCHENTAGE VARCHAR(255),
            PRIMARY KEY (STANDORTID)
        )
    """)
    cursor.execute("TRUNCATE TABLE lm_tourenplan_aggregiert")

    # Daten abfragen und transformieren
    query = """
        SELECT 
        STANDORTID,
        GROUP_CONCAT(
            CASE WOCHENTAG
            WHEN 1 THEN 'Montag'
            WHEN 2 THEN 'Dienstag'
            WHEN 3 THEN 'Mittwoch'
            WHEN 4 THEN 'Donnerstag'
            WHEN 5 THEN 'Freitag'
            WHEN 6 THEN 'Samstag'
            WHEN 7 THEN 'Sonntag'
            END
            ORDER BY WOCHENTAG SEPARATOR ','
        ) AS WOCHENTAGE,
        NOW() AS AKTUELLE_DATETIME
        FROM (
            SELECT STANDORTID, WOCHENTAG
            FROM lm_tourenplan
            GROUP BY STANDORTID, WOCHENTAG
        ) x
        GROUP BY STANDORTID
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    insert_sql = """
        INSERT INTO lm_tourenplan_aggregiert (STANDORTID, WOCHENTAGE, DATUM_ERSTELLT)
        VALUES (%s, %s, %s)
    """

    for row in rows:
        cursor.execute(insert_sql, row)

    connection.commit()
    cursor.close()
    connection.close()

    print(f"Aggregation abgeschlossen. {len(rows)} Datensätze eingefügt.")


# Hauptlogik starten ##################################################################################################################################
try:
    filepath = get_latest_file()
    import_tourenplan_csv_to_mysql(filepath)
    aggregate_wochentage_and_insert()
except Exception as e:
    print(f"Fehler: {e}")
    send_error_notification(str(e))
