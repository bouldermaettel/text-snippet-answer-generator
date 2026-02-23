# Benutzerhandbuch – Snippet Answer

## Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Anmeldung und Registrierung](#anmeldung-und-registrierung)
3. [Die Sammlung (Collection)](#die-sammlung-collection)
   - [Gruppierte Snippet-Ansicht](#gruppierte-snippet-ansicht)
   - [Snippets filtern](#snippets-filtern)
   - [Snippet manuell hinzufügen](#snippet-manuell-hinzufügen)
   - [Dateien hochladen](#dateien-hochladen)
   - [Snippet bearbeiten (Mehrsprachiger Editor)](#snippet-bearbeiten-mehrsprachiger-editor)
   - [Gruppe direkt ändern](#gruppe-direkt-ändern)
   - [Snippet löschen](#snippet-löschen)
4. [Fragen stellen (Ask)](#fragen-stellen-ask)
   - [Suchbereich festlegen](#suchbereich-festlegen)
   - [Erweiterte Optionen](#erweiterte-optionen)
   - [Antwort und Quellen](#antwort-und-quellen)
   - [Abschlussgruss](#abschlussgruss)
   - [Antwort kopieren](#antwort-kopieren)
5. [Antwort verfeinern (Refine)](#antwort-verfeinern-refine)
6. [Quellenkarten und verknüpfte Sprachen](#quellenkarten-und-verknüpfte-sprachen)
7. [Administration (nur Admins)](#administration-nur-admins)
   - [Benutzerverwaltung](#benutzerverwaltung)
   - [Sammlung importieren und exportieren](#sammlung-importieren-und-exportieren)
   - [Prompt-Verwaltung](#prompt-verwaltung)
   - [Backup und Wiederherstellung](#backup-und-wiederherstellung)
8. [Design-Modus (Theme)](#design-modus-theme)

---

## Überblick

**Snippet Answer** ist ein KI-gestütztes Frage-Antwort-System. Es basiert auf dem Prinzip der sogenannten *Retrieval-Augmented Generation* (RAG): Du pflegst eine Sammlung von Textbausteinen (Snippets), stellst Fragen in natürlicher Sprache und erhältst passende Antworten, die direkt aus deinen Snippets generiert werden – inklusive Quellenangaben und Konfidenzwerten.

**Typischer Ablauf:**

1. Snippets anlegen oder als Dateien hochladen
2. Eine Frage eingeben
3. Eine generierte Antwort mit Quellenangaben erhalten
4. Die Antwort bei Bedarf verfeinern

---

## Anmeldung und Registrierung

### Registrierung

Beim ersten Besuch der Anwendung erscheint die Anmeldeseite. Falls du noch kein Konto hast, wechsle auf **Registrieren** und gib deine E-Mail-Adresse sowie ein Passwort ein.

> **Hinweis:** Nach der Registrierung hat dein Konto den Status *ausstehend*. Ein Administrator muss dein Konto erst freischalten, bevor du dich anmelden kannst.

### Anmeldung

Gib deine E-Mail-Adresse und dein Passwort ein und klicke auf **Anmelden**. Nach erfolgreicher Anmeldung gelangst du zur Hauptansicht der Anwendung.

---

## Die Sammlung (Collection)

Die Sammlung ist der zentrale Ort, an dem alle deine Textbausteine (Snippets) verwaltet werden. Du erreichst die Sammlung über den Menüpunkt **Collection** in der Seitenleiste.

### Gruppierte Snippet-Ansicht

Snippets werden in der Sammlung als **gruppierte Karten** angezeigt. Jede Karte fasst alle Sprachversionen eines Snippets zusammen:

- **Sprach-Badges** zeigen die verfügbaren Sprachen an (z. B. DE, EN, FR, IT). Ein Klick auf einen Sprach-Badge zeigt die Vorschau in dieser Sprache.
- Automatisch generierte Übersetzungen sind mit einem **Stern (\*)** gekennzeichnet und farblich hervorgehoben.
- **Metadaten-Badges** zeigen vorhandene Zusatzinformationen an: Überschrift, Kategorie, Anweisungen (teal „Instr.") und Voraussetzungen (rosa „Prereq.").

### Snippets filtern

Um gezielt nach Snippets zu suchen, stehen dir mehrere Filtermöglichkeiten zur Verfügung:

| Filter | Beschreibung |
|--------|-------------|
| **Gruppe** | Wähle in der Seitenleiste eine bestimmte Gruppe aus, um nur deren Snippets anzuzeigen. |
| **Sprache** | Filtere nach Sprache (Deutsch, Englisch, Französisch, Italienisch). |
| **Textsuche** | Gib einen Suchbegriff ein, um Snippets nach Titel oder Inhalt zu durchsuchen. |

### Snippet manuell hinzufügen

1. Klicke in der Sammlungsansicht auf **Add snippet**.
2. Fülle das Formular aus:
   - **Titel** – Ein aussagekräftiger Name für das Snippet.
   - **Gruppe** – Wähle eine bestehende Gruppe aus oder erstelle eine neue, indem du einen neuen Namen eintippst.
   - **Sprache** – Wähle die Sprache des Textes (Auto, Deutsch, Englisch, Französisch, Italienisch).
   - **Text** – Der eigentliche Textinhalt des Snippets.
3. Optional kannst du unter **Erweitert** zusätzliche Metadaten angeben:
   - **Überschrift** – Eine Überschrift oder Abschnittsbezeichnung.
   - **Kategorie** – Eine inhaltliche Kategorie.
   - **Verknüpfte Snippets** – Kommagetrennte IDs von zusammengehörigen Snippets (z. B. Übersetzungen).
   - **PII anonymisieren** – Aktiviere diese Option, um personenbezogene Daten vor dem Speichern automatisch zu anonymisieren.
4. Klicke auf **Add snippet**, um das Snippet zur Sammlung hinzuzufügen.

### Dateien hochladen

Anstatt Snippets manuell einzugeben, kannst du auch Dateien importieren:

1. Klicke auf **Add snippet** und wechsle zum Tab **Upload**.
2. Wähle eine oder mehrere Dateien aus. Unterstützte Formate:
   - `.txt` (Textdateien)
   - `.docx` (Word-Dokumente)
   - `.pdf` (PDF-Dokumente)
3. Optional kannst du einen **Ordner** auswählen – der Ordnername wird dann als Gruppenname verwendet.
4. Optional kannst du **PII anonymisieren** aktivieren.
5. Jede hochgeladene Datei wird als ein eigenes Snippet angelegt. Bei PDF- und Word-Dateien wird der Originaltext extrahiert und das Originaldokument gespeichert, sodass es später über „View original document" abgerufen werden kann.

### Snippet bearbeiten (Mehrsprachiger Editor)

1. Klicke auf einer Snippet-Karte auf **Edit**.
2. Es öffnet sich der **gruppierte Editor** mit Sprach-Tabs:
   - Oben siehst du einen Tab pro verfügbarer Sprache (z. B. DE, EN, FR, IT). Automatisch übersetzte Sprachen sind mit einem **Stern (\*)** markiert.
   - Wähle einen Tab, um den Text und die Beispielfragen für diese Sprachversion zu bearbeiten.
3. Im oberen Bereich des Dialogs befinden sich die **gemeinsamen Felder**, die für alle Sprachversionen gelten:
   - **Titel** – Name des Snippets.
   - **Gruppe** – Zugehörige Gruppe (auswählbar oder neu erstellbar).
   - **Überschrift** – Optionale Abschnittsbezeichnung.
   - **Kategorie** – Optionale inhaltliche Kategorie.
   - **Anweisungen / Verfahren** – Optionale Handlungsanweisungen oder Verfahrensbeschreibungen, die im Quellenkarten-Bereich als ausklappbarer Abschnitt angezeigt werden.
   - **Voraussetzungen** – Optionale Voraussetzungen, die ebenfalls als ausklappbarer Abschnitt auf der Quellenkarte erscheinen.
4. Pro Sprach-Tab kannst du bearbeiten:
   - **Text** – Der Textinhalt in dieser Sprache.
   - **Beispielfragen** – Typische Fragen zu diesem Snippet (eine pro Zeile). Diese verbessern die Suchqualität bei der Fragebeantwortung erheblich.
5. Klicke auf **Save**, um die Änderungen zu speichern.

### Gruppe direkt ändern

Du kannst die Gruppenzugehörigkeit eines Snippets direkt in der Sammlungsansicht ändern, ohne den vollständigen Bearbeitungsdialog zu öffnen:

1. Klicke auf den **Gruppen-Badge** (den farbigen Tag mit dem Gruppennamen) auf einer Snippet-Karte.
2. Es öffnet sich ein Dropdown, in dem du eine bestehende Gruppe auswählen oder einen neuen Gruppennamen eingeben kannst.
3. Die Änderung wird sofort gespeichert.

### Snippet löschen

1. Klicke auf einer Snippet-Karte auf **Delete**.
2. Bestätige die Löschung im angezeigten Dialog.

> **Achtung:** Gelöschte Snippets können nicht wiederhergestellt werden. Auch eventuell gespeicherte Originaldokumente werden mit entfernt.

---

## Fragen stellen (Ask)

Die Kernfunktion der Anwendung. Wechsle über die Seitenleiste zum Bereich **Ask**.

1. Gib deine Frage in das Textfeld ein.
2. Klicke auf **Ask** oder drücke die **Eingabetaste**.

Die Anwendung durchsucht deine Snippet-Sammlung, findet die relevantesten Textbausteine und generiert eine Antwort.

> **Tipp:** Mit **Shift+Enter** kannst du im Fragefeld einen Zeilenumbruch einfügen, ohne die Frage abzusenden.

### Suchbereich festlegen

Oberhalb des Eingabefeldes kannst du den Suchbereich einschränken:

| Option | Beschreibung |
|--------|-------------|
| **All snippets** | Es wird in der gesamten Sammlung gesucht. |
| **Selected groups** | Wähle eine oder mehrere Gruppen aus, in denen gesucht werden soll. Eine Suchfunktion hilft beim Finden der gewünschten Gruppen. |
| **Selected snippets** | Wähle gezielt einzelne Snippets aus, auf die sich die Suche beschränken soll. |

### Erweiterte Optionen

| Option | Beschreibung |
|--------|-------------|
| **Answer closeness** (Antwortnähe) | Ein Schieberegler von 0 % bis 100 %. Je höher der Wert, desto näher bleibt die generierte Antwort am Originaltext der Snippets. Bei niedrigen Werten formuliert das System freier. |
| **HyDE** | Hypothetical Document Embeddings – eine fortgeschrittene Suchtechnik, bei der zuerst eine hypothetische Antwort generiert und dann nach ähnlichen Snippets gesucht wird. Dies kann die Suchergebnisse bei komplexen Fragen verbessern. |
| **Keyword reranking** | Ergänzt die semantische Suche um eine schlüsselwortbasierte Neugewichtung der Ergebnisse. Nützlich, wenn bestimmte Fachbegriffe exakt übereinstimmen sollen. |
| **Search in** (Sprache) | Einschränkung der Suche auf eine bestimmte Sprache (Alle, Deutsch, Englisch, Französisch, Italienisch). |

### Antwort und Quellen

Nach dem Absenden der Frage erhältst du:

- **Antwort** – Der generierte Antworttext. URLs in der Antwort werden automatisch als klickbare Links dargestellt.
- **Antwort-Konfidenz** – Ein Prozentwert, der angibt, wie sicher das System bezüglich der Antwort ist:
  - **Grün (hoch):** Hohe Übereinstimmung mit den Quellen.
  - **Gelb (mittel):** Mäßige Übereinstimmung.
  - **Rot (niedrig):** Geringe Übereinstimmung – die Antwort sollte kritisch geprüft werden.
- **Quellenkarten** – Unterhalb der Antwort werden die verwendeten Quell-Snippets aufgelistet (siehe [Quellenkarten und verknüpfte Sprachen](#quellenkarten-und-verknüpfte-sprachen)).

### Abschlussgruss

Unterhalb der Antwort wird automatisch ein **Abschlussgruss** angezeigt. Dieser wird vom Server vorgegeben und kann pro Sitzung im dafür vorgesehenen Textfeld angepasst werden.

- Der Standard-Abschlussgruss wird vom Administrator über die **Prompt-Verwaltung** festgelegt (Prompt: `default_closing`).
- Änderungen am Abschlussgruss im Textfeld gelten nur für die aktuelle Sitzung und werden nicht dauerhaft gespeichert.

### Antwort kopieren

Klicke auf die Schaltfläche **Kopieren** oberhalb der Antwort, um den gesamten Antworttext inklusive Abschlussgruss in die Zwischenablage zu kopieren. Nach erfolgreichem Kopieren wechselt die Beschriftung kurzzeitig zu „Kopiert".

---

## Antwort verfeinern (Refine)

Wenn die generierte Antwort nicht deinen Vorstellungen entspricht, kannst du sie verfeinern:

1. Unterhalb der Antwort findest du das **Verfeinerungsfeld**.
2. Gib eine Anweisung ein, wie die Antwort angepasst werden soll, z. B.:
   - „Mach die Antwort kürzer"
   - „Formuliere freundlicher"
   - „Fokussiere dich auf den rechtlichen Aspekt"
   - „Antworte auf Deutsch"
3. **Quellen auswählen (optional):** Klicke bei den Quellenkarten auf **Include**, um nur bestimmte Quellen für die Verfeinerung zu berücksichtigen. Wenn keine Quellen ausgewählt sind, werden alle Quellen verwendet.
4. Klicke auf **Refine**.

Die verfeinerte Antwort ersetzt die bisherige Antwort. Die Quellenkarten bleiben erhalten, sodass du den Vorgang beliebig oft wiederholen kannst.

> **Tipp:** Mit **Shift+Enter** kannst du auch im Verfeinerungsfeld einen Zeilenumbruch einfügen, ohne die Verfeinerung abzusenden.

---

## Quellenkarten und verknüpfte Sprachen

Jede Quellenkarte zeigt folgende Informationen:

| Element | Beschreibung |
|---------|-------------|
| **Titel / Abschnittsbezeichnung** | Name und ggf. Abschnitt des Quell-Snippets. |
| **Konfidenz** | Prozentwert der Übereinstimmung dieses Snippets mit der Frage. |
| **Badges** | Sprache, Überschrift, Kategorie, Anweisungen (teal), Voraussetzungen (rosa) und ob es sich um eine automatische Übersetzung handelt. |
| **Text** | Der Textinhalt des Snippets (bei langen Texten ein-/ausklappbar). |
| **Anweisungen / Verfahren** | Falls vorhanden, ein ausklappbarer Abschnitt mit Handlungsanweisungen oder Verfahrensbeschreibungen. |
| **Voraussetzungen** | Falls vorhanden, ein ausklappbarer Abschnitt mit den Voraussetzungen für das beschriebene Verfahren. |
| **View original document** | Öffnet das Originaldokument (PDF/DOCX), falls beim Upload gespeichert. |
| **Include / Included** | Markiert dieses Snippet als Kontext für die Verfeinerung. |
| **All languages** | Zeigt verknüpfte Übersetzungen dieses Snippets in anderen Sprachen an. Es öffnet sich ein Dialog mit allen verfügbaren Sprachversionen. |
| **Edit** | Öffnet den Bearbeitungsdialog für dieses Snippet (identisch zur Bearbeitung in der Sammlung). |

---

## Administration (nur Admins)

Als Administrator stehen dir in der Seitenleiste die zusätzlichen Menüpunkte **Users** und **Prompts** zur Verfügung. Ausserdem hast du in der Sammlungsansicht Zugriff auf Import- und Export-Funktionen.

### Benutzerverwaltung

Über den Menüpunkt **Users** verwaltest du alle Benutzerkonten. In der Benutzerliste werden für jeden Benutzer E-Mail, Rolle, Status und Erstellungsdatum angezeigt.

| Aktion | Beschreibung |
|--------|-------------|
| **Benutzer genehmigen** | Neu registrierte Benutzer haben den Status *ausstehend*. Klicke auf **Approve**, um den Zugang freizuschalten. |
| **Benutzer hinzufügen** | Klicke auf **Add user** und gib E-Mail, Passwort (mind. 8 Zeichen) und Rolle (Benutzer oder Admin) ein. Der neue Benutzer ist sofort aktiv und muss nicht separat genehmigt werden. |
| **Rolle ändern** | Über das Rollen-Dropdown in der Benutzerliste kannst du einen Benutzer zum Admin befördern oder einem Admin die Admin-Rechte entziehen. Der letzte verbleibende Admin kann nicht herabgestuft werden. |
| **Benutzer löschen** | Klicke auf **Delete**, um einen Benutzer zu entfernen. Der letzte verbleibende Admin kann nicht gelöscht werden. |

> **Hinweis:** Der erste Admin-Benutzer wird beim Start der Anwendung automatisch aus den Umgebungsvariablen `ADMIN_EMAIL` und `ADMIN_PASSWORD` erstellt, sofern noch kein Admin existiert.

### Sammlung importieren und exportieren

In der Sammlungsansicht (**Collection**) stehen Admins die Schaltflächen **Import JSON** und **Export JSON** zur Verfügung.

#### Sammlung exportieren

1. Setze optional die gewünschten Filter (Gruppe, Sprache), um nur einen Teil der Sammlung zu exportieren.
2. Klicke auf **Export JSON**.
3. Eine JSON-Datei mit dem Namen `collection-export-JJJJ-MM-TT.json` wird heruntergeladen.

Die exportierte Datei enthält alle Snippets im gruppierten Format als JSON-Array. Jedes Objekt umfasst Titel, Gruppe, gemeinsame Metadaten und ein `translations`-Objekt mit allen Sprachversionen. Laufzeit-Metadaten werden beim Export entfernt.

#### Sammlung importieren

1. Klicke auf **Import JSON** und wähle eine `.json`-Datei aus.
2. Die Datei muss ein JSON-Array mit gruppierten Snippet-Objekten enthalten (dasselbe Format wie beim Export).
3. Beim Import werden bestehende Snippets in den Gruppen, die in der Datei enthalten sind, **ersetzt**. Gruppen, die nicht in der Importdatei vorkommen, bleiben unverändert.
4. Nach erfolgreichem Import wird eine Zusammenfassung angezeigt (Anzahl importierter Snippets, Übersetzungen, betroffene Gruppen).

> **Tipp:** Nutze die Export-Funktion, um ein Backup deiner Sammlung zu erstellen, bevor du einen Import durchführst.

### Prompt-Verwaltung

Über den Menüpunkt **Prompts** kannst du die LLM-Prompt-Vorlagen anpassen, die das System für die Antwortgenerierung verwendet.

Die Prompts sind in zwei Bereiche unterteilt:

| Bereich | Beschreibung |
|---------|-------------|
| **Main Prompts** | Die wichtigsten Prompts, die den Antwortstil und den Abschlussgruss steuern. Hier befindet sich auch der Prompt `default_closing`, der den Standard-Abschlussgruss für alle Benutzer festlegt. |
| **Advanced prompts** | Erweiterte Prompts für Spezialfunktionen wie HyDE-Generierung, Übersetzung, Beispielfragen-Generierung und weitere interne Verarbeitungsschritte. Dieser Bereich ist standardmässig eingeklappt. |

| Aktion | Beschreibung |
|--------|-------------|
| **Prompt anzeigen** | Alle verfügbaren Prompt-Vorlagen werden mit ihrem Namen und aktuellem Text aufgelistet. |
| **Prompt bearbeiten** | Klicke auf einen Prompt, um den Text im Textfeld anzupassen. Klicke anschliessend auf **Save**, um die Änderung zu speichern. |
| **Prompt zurücksetzen** | Klicke auf **Reset to default**, um einen Prompt auf seinen ursprünglichen Standardtext zurückzusetzen. |

Änderungen an den Prompts wirken sich sofort auf alle nachfolgenden Antwortgenerierungen aus. Die angepassten Prompts werden serverseitig in einer separaten Datei gespeichert und überstehen Neustarts der Anwendung.

> **Achtung:** Änderungen an den Prompts können die Qualität und das Verhalten der generierten Antworten erheblich beeinflussen. Teste Anpassungen sorgfältig.

### Backup und Wiederherstellung

Für die vollständige Datensicherung stehen zwei API-Endpunkte zur Verfügung (ohne grafische Oberfläche):

| Endpunkt | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/admin/backup` | GET | Lädt ein `.tar.gz`-Archiv des gesamten Datenverzeichnisses herunter (Datenbank, Vektordatenbank, hochgeladene Dokumente). |
| `/api/admin/restore` | POST | Stellt die Anwendungsdaten aus einem zuvor erstellten `.tar.gz`-Backup wieder her. Die bestehenden Daten werden dabei vollständig ersetzt. |

Diese Endpunkte erfordern einen gültigen Admin-Token und können z. B. per `curl` aufgerufen werden:

```bash
# Backup erstellen
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  https://<server>/api/admin/backup -o backup.tar.gz

# Backup wiederherstellen
curl -X POST -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -F "file=@backup.tar.gz" \
  https://<server>/api/admin/restore
```

> **Achtung:** Die Wiederherstellung ersetzt alle bestehenden Daten (Snippets, Benutzer, Einstellungen). Die Anwendung wird dabei neu initialisiert.

---

## Design-Modus (Theme)

Unten in der Seitenleiste findest du den **Theme-Umschalter** mit drei Optionen:

| Modus | Beschreibung |
|-------|-------------|
| **Light** | Helles Design. |
| **Dark** | Dunkles Design. |
| **System** | Passt sich automatisch an die Systemeinstellung deines Betriebssystems an. |

Die Einstellung wird im Browser gespeichert und bleibt auch nach dem Schließen erhalten.

---

## Tipps für die beste Nutzung

- **Aussagekräftige Titel vergeben** – Gute Titel helfen dir, Snippets in der Sammlung schnell wiederzufinden.
- **Gruppen sinnvoll nutzen** – Organisiere deine Snippets thematisch in Gruppen, um den Suchbereich gezielt einschränken zu können. Über den Gruppen-Badge kannst du die Zuordnung jederzeit schnell ändern.
- **Beispielfragen pflegen** – Hinterlege bei wichtigen Snippets typische Fragen. Das verbessert die Trefferqualität bei der Suche erheblich.
- **Anweisungen und Voraussetzungen nutzen** – Für verfahrenstechnische Snippets kannst du Handlungsanweisungen und Voraussetzungen als separate Metadaten erfassen. Diese werden auf den Quellenkarten übersichtlich als ausklappbare Abschnitte dargestellt.
- **Antwortnähe anpassen** – Für wörtliche Zitate setze den Regler hoch; für freiere Zusammenfassungen niedrig.
- **Quellen prüfen** – Kontrolliere bei wichtigen Antworten immer die angezeigten Quellen und deren Konfidenzwerte.
- **Verfeinerung nutzen** – Wenn die erste Antwort nicht passt, formuliere eine klare Verfeinerungsanweisung, anstatt die Frage komplett neu zu stellen.
- **Abschlussgruss anpassen** – Passe den Abschlussgruss im Ask-Bereich für deine Sitzung an. Der Standardtext kann vom Administrator über die Prompt-Verwaltung zentral geändert werden.
- **Antwort kopieren** – Nutze die Kopieren-Schaltfläche, um Antwort und Abschlussgruss in einem Schritt in die Zwischenablage zu übernehmen.
- **Sprachübergreifend suchen** – Die Anwendung unterstützt mehrsprachige Suche. Stelle Fragen in einer beliebigen Sprache, auch wenn deine Snippets in einer anderen Sprache vorliegen.
