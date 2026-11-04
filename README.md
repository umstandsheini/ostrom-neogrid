# Ostrom NeoGrid für Home Assistant

Inoffizielle Home-Assistant-Integration für Ostrom (NeoGrid-Gutschriften, Fahrzeuge, Wallbox, Heizung, Zähler).
Sie nutzt die **private API der Ostrom-App** (aus der Android-App 6.4.0 per Analyse des JS-Bundles abgeleitet),
nicht die offizielle Entwickler-API, weil diese keine Steuerfunktionen hat.

> **Hinweis:** Nicht von Ostrom unterstützt oder geprüft. Die private API kann sich jederzeit ändern oder wegfallen.
> Ob die Nutzungsbedingungen das erlauben, ist nicht geprüft. Nutzung auf eigene Verantwortung, nur mit dem eigenen Konto.

## Funktionen

- **Fahrzeuge:** Akku, Reichweite, Ladezustand, Ladeleistung, Restladezeit; Schalter *NeoGrid*; Ziel-Ladestand; *Fertig bis*;
  Tasten *Laden starten* / *Laden stoppen*; Sitzungsstatus der NeoGrid-Sitzung.
- **Wallbox:** Ladezustand, *Optimiertes Laden*, *Fertig bis*.
- **Heizung (Bosch via Enode):** Klima-Entität mit Ein/Aus und Solltemperatur. Der Weg zurück zum Zeitplan ist nicht eingebaut.
- **Vertrag:** Zählerstand (letzte Ablesung und geschätzt), Verbrauch, Abschlag, Saldo, Gutschriften, CO₂.
- **NeoGrid-Statistik pro Fahrzeug:** geladene NeoGrid-kWh, Gutschrift, Vorteil in ct/kWh, letzter Ladetag.
- **Gutschriften:** Sensor *letzte Gutschrift*, Ereignis `ostrom_neogrid_credit` und Benachrichtigung bei einer neuen Buchung.
- **Erwartete Gutschrift** als Schätzung aus kWh bis zum Ziel, Basiswert (ct/kWh) und Aktionsfaktor (beides einstellbar).

Nicht möglich: der in der App angelegte Override (*Jetzt laden*), der Pfad antwortet mit 404.

## Installation

1. Ordner `custom_components/ostrom_neogrid` nach `/config/custom_components/` kopieren.
2. Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → **Ostrom NeoGrid**, E-Mail und Passwort des Ostrom-Kontos eingeben.

Das Passwort wird wie bei anderen Cloud-Integrationen im Konfigurationseintrag von Home Assistant gespeichert.
Das Passwort änderst du unter Einstellungen → Geräte & Dienste → Ostrom NeoGrid → ⋮ → **Neu konfigurieren**; es wird geprüft,
bevor es gespeichert wird. Lehnt Ostrom den Login später ab, fragt Home Assistant selbst nach dem neuen Passwort.

## Entwicklung

- `ostrom_app_findings.md`: gefundene Endpunkte und Nachweise aus dem App-Code.
- `tools/hbc_strings.py`: liest die String-Tabelle eines Hermes-Bytecode-Bundles (nur lesend, lokal).
- `ostrom_client.py` und `probe_*.py` / `test_*.py`: kleine Skripte zum Ausprobieren der API. Zugangsdaten über die
  Umgebungsvariablen `OSTROM_EMAIL` und `OSTROM_PASSWORD` setzen; schreibende Tests an einem nicht angesteckten Fahrzeug
  ausführen und den Ausgangszustand wiederherstellen.

Eigene Auswertungen (`neogrid_*.csv`, `analysis/`) gehören nicht ins Repository (siehe `.gitignore`).
