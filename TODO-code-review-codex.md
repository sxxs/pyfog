# Code-Review Codex

Stand: 2026-09-05, Commit `d9eb2a6` (`Add a live dashboard with key-switchable views`).

Geprüft: alle Python-Module, CLI/Rendering, Packaging, Docker-Konfiguration sowie Tests und SQL-Fixtures. Keine Implementierungsänderungen. Das parallele Claude-Review wurde nicht bearbeitet.

Alle acht Punkte sind umgesetzt (siehe Git-Historie nach `d9eb2a6`).

Prioritäten: **P1** = zentrale Funktion liefert falsche Ergebnisse; **P2** = funktionaler Fehler unter den beschriebenen Bedingungen. Die Checkboxen sind offene Umsetzungspunkte.

## Findings

### 1. [P1] Live-Ansichten behalten denselben Datenbank-Snapshot

- [x] Transaktion pro Aktualisierung beenden oder die Verbindung für diese SELECT-Abfragen mit Autocommit betreiben.

**Stellen:** `pyfog/db.py:24–27`, `pyfog/db.py:35–45`, `pyfog/cli.py:292–297`.

PyMySQL verwendet standardmäßig `autocommit=False`; der Konstruktor überschreibt das nicht. Die Watch-Schleife verwendet dieselbe Verbindung für jede Aktualisierung und ruft weder Commit noch Rollback auf. Bei InnoDB mit REPEATABLE READ bleiben dadurch Tabellenabfragen beim Snapshot der ersten konsistenten Abfrage. Neue `Fog`-Instanzen ändern daran nichts. Tasks und Fortschritte bleiben stehen, während `SELECT NOW()` und die Statuszeile weiterlaufen; vermeintlich aktuelle Tasks können dadurch sogar fälschlich als stale erscheinen. Eine dauerhaft offene Lesetransaktion hält außerdem alte Zeilenversionen fest.

**Beleg:** Default anhand der installierten PyMySQL-Signatur geprüft; die mitgelieferten Tabellen verwenden InnoDB. Transaktionsverhalten aus dem Code abgeleitet, nicht gegen eine laufende Datenbank reproduziert.

**Prüfung nach Fix:** Watch starten, in einer zweiten Verbindung einen Task ändern und committen. Spätestens der nächste Refresh muss den neuen Zustand zeigen, ohne Neuverbindung.

### 2. [P2] JSON mit `--watch` enthält Terminalcodes und verliert Daten

- [x] Für JSON einen vollständigen, dokumentierten Ausgabestrom verwenden oder die Kombination mit Watch ausdrücklich ablehnen.

**Stelle:** `pyfog/cli.py:298–315`.

Auch bei `tasks --json --watch 1` und `multicast --json --watch 1` gelangt das serialisierte JSON zusammen mit einer Statuszeile in `render.frame()`. Das fügt ANSI-Steuersequenzen ein und beschneidet Zeilen sowie die gesamte Ausgabe auf Terminalgröße. Auch bei Umleitung in eine Datei entsteht kein maschinenlesbares JSON; größere Ergebnisse werden unwiederbringlich abgeschnitten.

**Reproduziert:** Ein einzelner Watch-Durchlauf mit 50 Zahlen beginnt mit `\x1b[Hpyfog tasks ...` und enthält `more lines` anstelle des vollständigen Arrays.

**Prüfung nach Fix:** Umgeleitete Watch-Ausgabe mit einem JSON-Parser lesen und auf Vollständigkeit prüfen, auch mit mehr Zeilen als der Terminalhöhe.

### 3. [P2] Remote-Sessions beanspruchen lokale Multicast-Sender

- [x] Prozess- und Logzuordnung auf nachweislich lokale Sessions beschränken; Remote-Sessions als lokal nicht prüfbar behandeln.

**Stelle:** `pyfog/fog.py:366–376`.

`sender_local` wird berechnet, schützt aber nur die Prüfung von `wrapper_alive`. Die Senderliste wird für jede Session allein über Port oder lokale PID-Nachfahren bestimmt. Verwendet eine Session auf einem anderen Storage-Node denselben Port wie ein lokaler Sender, wird dieser ihr zugeordnet und aus `orphan_senders` entfernt. Auch eine zufällig gleiche PID kann falsch zuordnen. Der lokale UDPcast-Logpfad wird ebenfalls für Remote-Sessions ausgewertet.

**Reproduziert:** Remote-Session mit Port 63100 und lokalem Sender PID 99 auf demselben Port ergibt `sender_local=False`, trotzdem `senders=[PID 99]` und keine Orphans.

**Prüfung nach Fix:** Zwei Nodes mit gleichem Port simulieren; der lokale Sender darf durch die Remote-Session nicht beansprucht werden.

### 4. [P2] Session-Limit und `--all` verfälschen die Orphan-Erkennung

- [x] Orphan-Zuordnung gegen alle aktiven lokalen Sessions durchführen, unabhängig von der für die Anzeige ausgewählten Teilmenge.

**Stellen:** `pyfog/fog.py:349–353`, `pyfog/fog.py:363–379`.

`claimed` wird ausschließlich aus den bereits gefilterten und begrenzten Sessions aufgebaut. Bei `multicast --limit 1` wird deshalb ein Sender einer zweiten aktiven Session als verwaist ausgegeben, wenn er keiner angezeigten Session zugeordnet werden kann. Umgekehrt dürfen mit `--all` auch abgeschlossene Sessions Sender beanspruchen: Ein alter Eintrag mit wiederverwendetem Port kann einen tatsächlich verwaisten Sender verdecken. Die Ausgabe behauptet ausdrücklich, dass keine aktive Session diese Prozesse beansprucht.

**Beleg:** Kontrollfluss und SQL-Limit im Code; kein Datenbank-Integrationstest durchgeführt.

**Prüfung nach Fix:** Zwei aktive Sessions bei Limit 1 sowie eine abgeschlossene Session mit gleichem Port wie ein unzugeordneter Sender testen.

### 5. [P2] Explizite Zugangsdaten umgehen unlesbare FOG-Konfiguration nicht

- [x] Vollständige CLI-/Umgebungs-Overrides auch dann zulassen, wenn die automatisch gefundene Konfiguration nicht lesbar ist.

**Stelle:** `pyfog/config.py:93–102`; Overrides folgen erst in `pyfog/config.py:120–132`.

Auf einem FOG-Server kann ein normaler Benutzer mit eigenem SELECT-Konto sämtliche `--db-*`-Argumente korrekt angeben und trotzdem vor der Verbindung scheitern: Die automatisch gefundene, beispielsweise nur für root lesbare PHP-Datei löst vorher `ConfigError` aus. Die Fehlermeldung empfiehlt ausgerechnet die bereits verwendeten `--db-*`-Optionen.

**Reproduziert:** `read_php_config()` mit `EACCES` simuliert und alle vier Zugangsdaten übergeben; `Settings` wirft dennoch `ConfigError`.

**Prüfung nach Fix:** Vollständige CLI- und Environment-Zugangsdaten jeweils mit unlesbarer automatisch gefundener Konfiguration testen. Ohne ausreichende Zugangsdaten soll ein verständlicher Fehler bleiben.

### 6. [P2] Unlesbare optionale Logs brechen Berichte und Dashboard ab

- [x] Lesefehler pro optionaler Logdatei behandeln und deren Nichtverfügbarkeit im Ergebnis kenntlich machen.

**Stellen:** `pyfog/local.py:132–146`, `pyfog/local.py:157–158`, `pyfog/local.py:188–190`; Fehlerbehandlung in `pyfog/cli.py:207–214` und `pyfog/cli.py:307`.

Die automatische Logsuche prüft nur `isfile()`. Ist eine vorhandene Access-Logdatei für das SELECT-Konto nicht lesbar, propagiert `PermissionError` bis zum ungeschützten CLI-Abbruch, statt `clients` wenigstens mit den Token-Zeiten auszugeben. Für UDPcast-Logs gilt dasselbe; damit kann schon `dashboard` abbrechen. Auch Rotation zwischen Existenzprüfung und Öffnen kann einen entsprechenden Fehler auslösen. Die Watch-Schleife fängt nur `DatabaseError` ab.

**Reproduziert:** Automatisch gefundenes Access-Log mit simuliertem `EACCES` lässt `Fog.clients()` mit `PermissionError` enden.

**Prüfung nach Fix:** Unlesbare und zwischenzeitlich entfernte Logs testen; verfügbare Daten müssen erhalten bleiben und der Live-Modus muss weiterlaufen.

### 7. [P2] Client-Zeitvergleich vermischt lokale und Datenbank-Zeitzone

- [x] Log-, Token- und Referenzzeiten vor dem Vergleich auf dieselbe Zeitzone beziehungsweise absolute Zeitbasis bringen; geplante Unix-Zeitstempel konsistent ausgeben.

**Stellen:** `pyfog/local.py:167–170`, `pyfog/fog.py:403–427`; zusätzlich `pyfog/fog.py:278–279`.

Access-Logzeiten werden in die lokale Zeitzone des Python-Prozesses konvertiert und anschließend ihrer Zeitzoneninformation beraubt. `clients()` vergleicht sie mit naiven Datenbankzeiten aus `hostSecTime` und `NOW()`. Bei unterschiedlicher DB-Session- und Prozesszeitzone werden Alter, Quellenwahl und Stale-Filter falsch. Das kann auch auf demselben Host bei einer DB-Session in UTC auftreten. `scheduled()` verwendet ebenfalls die Prozesszeitzone, obwohl die Datenebene Zeitstempel in Datenbank-Serverzeit verspricht.

**Reproduziert:** DB-Zeit `2026-09-05 10:00:00` in UTC, gleichzeitiger Logeintrag `10:00:00 +0000`, Prozess in `Europe/Berlin`: Ausgabe `last_seen=12:00:00`, `age=-7200`.

**Prüfung nach Fix:** Dieselben Ereignisse mit unterschiedlichen Prozess- und DB-Zeitzonen müssen dasselbe Alter und dieselbe Quellenwahl ergeben.

### 8. [P2] Dokumentierter Testaufruf führt keine Tests aus

- [x] Testverzeichnis für Standard-Discovery zugänglich machen oder überall den tatsächlich funktionierenden Discovery-Aufruf dokumentieren und verwenden.

**Stellen:** `tests/` ohne `__init__.py`, `tests/test_units.py:1`, README-Abschnitt „Verification“.

Der dokumentierte Aufruf `python3 -m unittest` entdeckt die Tests im Unterverzeichnis nicht. So kann die behauptete Unit-Verifikation vollständig ausfallen; je nach Python-Version wird ein Lauf ohne Tests unterschiedlich quittiert.

**Reproduziert:** Unter Python 3.14.3 meldet der dokumentierte Aufruf `Ran 0 tests` / `NO TESTS RAN` mit Exitcode 5. Explizite Discovery findet dagegen alle 18 Tests.

**Prüfung nach Fix:** Der dokumentierte Befehl muss aus dem Repository-Root tatsächlich die 18 vorhandenen Tests ausführen.

## Durchgeführte Verifikation und Grenzen

- `uv run --no-project --with pymysql python -m unittest discover -s tests -v`: **18 Tests bestanden**. PyMySQL war im System-Python zunächst nicht installiert und wurde für den Testlauf über uv bereitgestellt.
- Kleine isolierte Reproduktionen für Findings 2, 3, 5, 6 und 7; bei externen Ressourcen mit Mocks, ohne Änderungen an Produktivdaten.
- Lokale PyMySQL-Signatur für Finding 1 geprüft; SQL und Datentypen gegen `tests/fog-schema.sql` gelesen.
- `docker compose ps`: keine laufenden Testservices. Kein Docker-Smoke-Test und kein Test gegen einen echten FOG-Server durchgeführt.
- FOG-spezifische Annahmen wurden anhand des Repositorys geprüft; kein Abgleich mit externem FOG-Quellcode. Die Liste konzentriert sich auf konkret belegbare Fehler und beansprucht keine vollständige Fehlerfreiheit der übrigen Bereiche.
