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
   python main_gum.py
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
 
## Struttura del Progetto

- `main_gum.py`: Interfaccia CLI interattiva con Gum.
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
