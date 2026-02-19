# Benutzerhandbuch – Snippet Answer

## Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Anmeldung und Registrierung](#anmeldung-und-registrierung)
3. [Die Sammlung (Collection)](#die-sammlung-collection)
   - [Snippets anzeigen und filtern](#snippets-anzeigen-und-filtern)
   - [Snippet manuell hinzufügen](#snippet-manuell-hinzufügen)
   - [Dateien hochladen](#dateien-hochladen)
   - [Snippet bearbeiten](#snippet-bearbeiten)
   - [Snippet löschen](#snippet-löschen)
4. [Fragen stellen (Ask)](#fragen-stellen-ask)
   - [Suchbereich festlegen](#suchbereich-festlegen)
   - [Erweiterte Optionen](#erweiterte-optionen)
   - [Antwort und Quellen](#antwort-und-quellen)
5. [Antwort verfeinern (Refine)](#antwort-verfeinern-refine)
6. [Quellenkarten und verknüpfte Sprachen](#quellenkarten-und-verknüpfte-sprachen)
7. [Benutzerverwaltung (nur Admins)](#benutzerverwaltung-nur-admins)
8. [Design-Modus (Theme)](#design-modus-theme)

---

## Überblick

**Snippet Answer** ist ein KI-gestütztes Frage-Antwort-System. Es basiert auf dem Prinzip der sogenannten *Retrieval-Augmented Generation* (RAG): Sie pflegen eine Sammlung von Textbausteinen (Snippets), stellen Fragen in natürlicher Sprache und erhalten passende Antworten, die direkt aus Ihren Snippets generiert werden – inklusive Quellenangaben und Konfidenzwerten.

**Typischer Ablauf:**

1. Snippets anlegen oder als Dateien hochladen
2. Eine Frage eingeben
3. Eine generierte Antwort mit Quellenangaben erhalten
4. Die Antwort bei Bedarf verfeinern

---

## Anmeldung und Registrierung

### Registrierung

Beim ersten Besuch der Anwendung erscheint die Anmeldeseite. Falls Sie noch kein Konto haben, wechseln Sie auf **Registrieren** und geben Sie Ihre E-Mail-Adresse sowie ein Passwort ein.

> **Hinweis:** Nach der Registrierung hat Ihr Konto den Status *ausstehend*. Ein Administrator muss Ihr Konto erst freischalten, bevor Sie sich anmelden können.

### Anmeldung

Geben Sie Ihre E-Mail-Adresse und Ihr Passwort ein und klicken Sie auf **Anmelden**. Nach erfolgreicher Anmeldung gelangen Sie zur Hauptansicht der Anwendung.

---

## Die Sammlung (Collection)

Die Sammlung ist der zentrale Ort, an dem alle Ihre Textbausteine (Snippets) verwaltet werden. Sie erreichen die Sammlung über den Menüpunkt **Collection** in der Seitenleiste.

### Snippets anzeigen und filtern

In der Sammlungsansicht sehen Sie alle vorhandenen Snippets als Karten. Um gezielt nach Snippets zu suchen, stehen Ihnen mehrere Filtermöglichkeiten zur Verfügung:

| Filter | Beschreibung |
|--------|-------------|
| **Gruppe** | Wählen Sie in der Seitenleiste eine bestimmte Gruppe aus, um nur deren Snippets anzuzeigen. |
| **Sprache** | Filtern Sie nach Sprache (Deutsch, Englisch, Französisch, Italienisch). |
| **Generierte Übersetzungen** | Aktivieren Sie „Show generated translations", um auch automatisch übersetzte Snippets anzuzeigen. |
| **Textsuche** | Geben Sie einen Suchbegriff ein, um Snippets nach Titel oder Inhalt zu durchsuchen. |

### Snippet manuell hinzufügen

1. Klicken Sie in der Sammlungsansicht auf **Add snippet**.
2. Füllen Sie das Formular aus:
   - **Titel** – Ein aussagekräftiger Name für das Snippet.
   - **Gruppe** – Wählen Sie eine bestehende Gruppe aus oder erstellen Sie eine neue, indem Sie einen neuen Namen eintippen.
   - **Sprache** – Wählen Sie die Sprache des Textes (Auto, Deutsch, Englisch, Französisch, Italienisch).
   - **Text** – Der eigentliche Textinhalt des Snippets.
3. Optional können Sie unter **Erweitert** zusätzliche Metadaten angeben:
   - **Überschrift** – Eine Überschrift oder Abschnittsbezeichnung.
   - **Kategorie** – Eine inhaltliche Kategorie.
   - **Verknüpfte Snippets** – Kommagetrennte IDs von zusammengehörigen Snippets (z. B. Übersetzungen).
   - **PII anonymisieren** – Aktivieren Sie diese Option, um personenbezogene Daten vor dem Speichern automatisch zu anonymisieren.
4. Klicken Sie auf **Add snippet**, um das Snippet zur Sammlung hinzuzufügen.

### Dateien hochladen

Anstatt Snippets manuell einzugeben, können Sie auch Dateien importieren:

1. Klicken Sie auf **Add snippet** und wechseln Sie zum Tab **Upload**.
2. Wählen Sie eine oder mehrere Dateien aus. Unterstützte Formate:
   - `.txt` (Textdateien)
   - `.docx` (Word-Dokumente)
   - `.pdf` (PDF-Dokumente)
3. Optional können Sie einen **Ordner** auswählen – der Ordnername wird dann als Gruppenname verwendet.
4. Optional können Sie **PII anonymisieren** aktivieren.
5. Jede hochgeladene Datei wird als ein eigenes Snippet angelegt. Bei PDF- und Word-Dateien wird der Originaltext extrahiert und das Originaldokument gespeichert, sodass es später über „View original document" abgerufen werden kann.

### Snippet bearbeiten

1. Klicken Sie auf einer Snippet-Karte auf **Edit**.
2. Im Bearbeitungsdialog können Sie alle Felder ändern:
   - Titel, Gruppe, Sprache, Text
   - Erweiterte Metadaten (Überschrift, Kategorie, verknüpfte Snippets)
   - **Beispielfragen** – Geben Sie hier Fragen ein (eine pro Zeile), die typischerweise zu diesem Snippet gestellt werden. Diese verbessern die Suchqualität bei der Fragebeantwortung.
3. Klicken Sie auf **Save**, um die Änderungen zu speichern.

### Snippet löschen

1. Klicken Sie auf einer Snippet-Karte auf **Delete**.
2. Bestätigen Sie die Löschung im angezeigten Dialog.

> **Achtung:** Gelöschte Snippets können nicht wiederhergestellt werden. Auch eventuell gespeicherte Originaldokumente werden mit entfernt.

---

## Fragen stellen (Ask)

Die Kernfunktion der Anwendung. Wechseln Sie über die Seitenleiste zum Bereich **Ask**.

1. Geben Sie Ihre Frage in das Textfeld ein.
2. Klicken Sie auf **Ask** oder drücken Sie die **Eingabetaste**.

Die Anwendung durchsucht Ihre Snippet-Sammlung, findet die relevantesten Textbausteine und generiert eine Antwort.

### Suchbereich festlegen

Oberhalb des Eingabefeldes können Sie den Suchbereich einschränken:

| Option | Beschreibung |
|--------|-------------|
| **All snippets** | Es wird in der gesamten Sammlung gesucht. |
| **Selected groups** | Wählen Sie eine oder mehrere Gruppen aus, in denen gesucht werden soll. Eine Suchfunktion hilft beim Finden der gewünschten Gruppen. |
| **Selected snippets** | Wählen Sie gezielt einzelne Snippets aus, auf die sich die Suche beschränken soll. |

### Erweiterte Optionen

| Option | Beschreibung |
|--------|-------------|
| **Answer closeness** (Antwortnähe) | Ein Schieberegler von 0 % bis 100 %. Je höher der Wert, desto näher bleibt die generierte Antwort am Originaltext der Snippets. Bei niedrigen Werten formuliert das System freier. |
| **HyDE** | Hypothetical Document Embeddings – eine fortgeschrittene Suchtechnik, bei der zuerst eine hypothetische Antwort generiert und dann nach ähnlichen Snippets gesucht wird. Dies kann die Suchergebnisse bei komplexen Fragen verbessern. |
| **Keyword reranking** | Ergänzt die semantische Suche um eine schlüsselwortbasierte Neugewichtung der Ergebnisse. Nützlich, wenn bestimmte Fachbegriffe exakt übereinstimmen sollen. |
| **Search in** (Sprache) | Einschränkung der Suche auf eine bestimmte Sprache (Alle, Deutsch, Englisch, Französisch, Italienisch). |

### Antwort und Quellen

Nach dem Absenden der Frage erhalten Sie:

- **Antwort** – Der generierte Antworttext.
- **Antwort-Konfidenz** – Ein Prozentwert, der angibt, wie sicher das System bezüglich der Antwort ist:
  - **Grün (hoch):** Hohe Übereinstimmung mit den Quellen.
  - **Gelb (mittel):** Mäßige Übereinstimmung.
  - **Rot (niedrig):** Geringe Übereinstimmung – die Antwort sollte kritisch geprüft werden.
- **Quellenkarten** – Unterhalb der Antwort werden die verwendeten Quell-Snippets aufgelistet (siehe nächster Abschnitt).

---

## Antwort verfeinern (Refine)

Wenn die generierte Antwort nicht Ihren Vorstellungen entspricht, können Sie sie verfeinern:

1. Unterhalb der Antwort finden Sie das **Verfeinerungsfeld**.
2. Geben Sie eine Anweisung ein, wie die Antwort angepasst werden soll, z. B.:
   - „Mach die Antwort kürzer"
   - „Formuliere freundlicher"
   - „Fokussiere dich auf den rechtlichen Aspekt"
   - „Antworte auf Deutsch"
3. **Quellen auswählen (optional):** Klicken Sie bei den Quellenkarten auf **Include**, um nur bestimmte Quellen für die Verfeinerung zu berücksichtigen. Wenn keine Quellen ausgewählt sind, werden alle Quellen verwendet.
4. Klicken Sie auf **Refine**.

Die verfeinerte Antwort ersetzt die bisherige Antwort. Die Quellenkarten bleiben erhalten, sodass Sie den Vorgang beliebig oft wiederholen können.

---

## Quellenkarten und verknüpfte Sprachen

Jede Quellenkarte zeigt folgende Informationen:

| Element | Beschreibung |
|---------|-------------|
| **Titel / Abschnittsbezeichnung** | Name und ggf. Abschnitt des Quell-Snippets. |
| **Konfidenz** | Prozentwert der Übereinstimmung dieses Snippets mit der Frage. |
| **Badges** | Sprache, Überschrift, Kategorie und ob es sich um eine automatische Übersetzung handelt. |
| **Text** | Der Textinhalt des Snippets (bei langen Texten ein-/ausklappbar). |
| **View original document** | Öffnet das Originaldokument (PDF/DOCX), falls beim Upload gespeichert. |
| **Include / Included** | Markiert dieses Snippet als Kontext für die Verfeinerung. |
| **All languages** | Zeigt verknüpfte Übersetzungen dieses Snippets in anderen Sprachen an. Es öffnet sich ein Dialog mit allen verfügbaren Sprachversionen. |
| **Edit** | Öffnet den Bearbeitungsdialog für dieses Snippet (identisch zur Bearbeitung in der Sammlung). |

---

## Benutzerverwaltung (nur Admins)

Administratoren sehen in der Seitenleiste den zusätzlichen Menüpunkt **Users**. Hier können folgende Aktionen durchgeführt werden:

| Aktion | Beschreibung |
|--------|-------------|
| **Benutzer genehmigen** | Neu registrierte Benutzer haben den Status *ausstehend*. Klicken Sie auf **Approve**, um den Zugang freizuschalten. |
| **Benutzer hinzufügen** | Erstellen Sie einen neuen Benutzer mit E-Mail, Passwort und Rolle (Benutzer oder Admin). Der Benutzer ist sofort aktiv. |
| **Benutzer löschen** | Entfernt einen Benutzer. Der letzte verbleibende Admin kann nicht gelöscht werden. |

In der Benutzerliste werden für jeden Benutzer E-Mail, Rolle, Status und Erstellungsdatum angezeigt.

---

## Design-Modus (Theme)

Unten in der Seitenleiste finden Sie den **Theme-Umschalter** mit drei Optionen:

| Modus | Beschreibung |
|-------|-------------|
| **Light** | Helles Design. |
| **Dark** | Dunkles Design. |
| **System** | Passt sich automatisch an die Systemeinstellung Ihres Betriebssystems an. |

Die Einstellung wird im Browser gespeichert und bleibt auch nach dem Schließen erhalten.

---

## Tipps für die beste Nutzung

- **Aussagekräftige Titel vergeben** – Gute Titel helfen Ihnen, Snippets in der Sammlung schnell wiederzufinden.
- **Gruppen sinnvoll nutzen** – Organisieren Sie Ihre Snippets thematisch in Gruppen, um den Suchbereich gezielt einschränken zu können.
- **Beispielfragen pflegen** – Hinterlegen Sie bei wichtigen Snippets typische Fragen. Das verbessert die Trefferqualität bei der Suche erheblich.
- **Antwortnähe anpassen** – Für wörtliche Zitate setzen Sie den Regler hoch; für freiere Zusammenfassungen niedrig.
- **Quellen prüfen** – Kontrollieren Sie bei wichtigen Antworten immer die angezeigten Quellen und deren Konfidenzwerte.
- **Verfeinerung nutzen** – Wenn die erste Antwort nicht passt, formulieren Sie eine klare Verfeinerungsanweisung, anstatt die Frage komplett neu zu stellen.
- **Sprachübergreifend suchen** – Die Anwendung unterstützt mehrsprachige Suche. Stellen Sie Fragen in einer beliebigen Sprache, auch wenn Ihre Snippets in einer anderen Sprache vorliegen.
