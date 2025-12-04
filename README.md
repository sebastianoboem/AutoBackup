# AutoBackup Portable
 
Un'applicazione portatile per il backup dei dati sviluppata in Python, progettata per essere semplice, efficace e senza installazione.
 
## Funzionalità
 
- **Wizard Intuitivo**: Guida passo-passo per la configurazione del backup.
- **Selezione Intelligente**: Rilevamento automatico delle unità USB.
- **Filtri Personalizzabili**: Seleziona categorie (Documenti, Foto, Video) o estensioni specifiche.
- **Esclusioni Sicure**: Ignora automaticamente cartelle di sistema (Windows, Program Files) e permette esclusioni manuali.
- **Backup Organizzato**: Mantiene la struttura originale delle cartelle all'interno di una suddivisione per categorie.
- **Verifica Integrità**: Controllo Hash MD5 opzionale per garantire la copia corretta.
- **Gestione Processo**: Pausa, Ripresa e Stop durante la copia.
 
## Requisiti

- Windows 10 o 11, oppure macOS 12+
- Python 3.8+ (solo per eseguire da sorgente o compilare)
- **ADB (Android Debug Bridge)**: Necessario solo per il backup da dispositivi Android.
 
## Installazione e Utilizzo
 
### 1. Eseguire da Sorgente

1. Installare le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
2. Installare Gum (solo macOS):
   ```bash
   brew install gum
   ```
3. Avviare l'applicazione:
   
   Puoi usare lo script automatico che gestisce le dipendenze:
   ```bash
   ./run_mac.sh
   ```
   
   Oppure manualmente:
   ```bash
   source .venv/bin/activate
   python main.py
   ```
 
### 2. Creare l'Eseguibile

Per distribuire l'applicazione come file unico portatile:

- Windows:
  ```bash
  python build_exe.py
  ```
- macOS:
  ```bash
  python build_mac.py
  ```

Troverai l'eseguibile nella cartella `dist`.

## Backup da Android

L'applicazione supporta il backup diretto da dispositivi Android tramite ADB.

### Configurazione Android
1. **Abilitare Opzioni Sviluppatore**: Vai su *Impostazioni > Info telefono* e tocca 7 volte su *Numero build*.
2. **Attivare Debug USB**: Vai su *Impostazioni > Sistema > Opzioni sviluppatore* e attiva *Debug USB*.
3. **Collegamento**: Collega il telefono al PC via USB.
4. **Autorizzazione**: Sul display del telefono apparirà una richiesta "Consenti debug USB?". Seleziona "Consenti sempre..." e conferma.

### Requisiti PC/Mac
- È necessario avere `adb` installato.
- Se `adb` è nel PATH di sistema, verrà rilevato automaticamente.
- In alternativa, posiziona l'eseguibile `adb` (e le relative librerie) nella stessa cartella di `AutoBackup`.

All'avvio dell'applicazione, seleziona la modalità **Backup da Android** e segui la procedura guidata.
 
## Struttura del Progetto
 
- `main.py`: Interfaccia CLI interattiva con Gum.
- `backup_engine.py`: Logica di core (scansione, copia, verifica).
- `build_exe.py`: Script di build Windows con PyInstaller.
- `build_mac.py`: Script di build macOS con PyInstaller.
- `launchd/com.autobackup.agent.plist`: Template per schedulazione automatica su macOS.

## Schedulazione automatica (macOS)

Per eseguire il backup in automatico su macOS:

1. Copia il file `launchd/com.autobackup.agent.plist` in `~/Library/LaunchAgents/` e modifica `USERNAME` e i percorsi.
2. Carica l'agente:
   ```bash
   launchctl load -w ~/Library/LaunchAgents/com.autobackup.agent.plist
   ```
3. Log disponibili in `~/Library/Logs/AutoBackup/`.
