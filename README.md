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
 
- Windows 10 o 11
- Python 3.8+ (solo per eseguire da sorgente o compilare)
 
## Installazione e Utilizzo
 
### 1. Eseguire da Sorgente
 
1. Installare le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
2. Avviare l'applicazione:
   ```bash
   python main.py
   ```
 
### 2. Creare l'Eseguibile (.exe)
 
Per distribuire l'applicazione come file unico portatile:
 
1. Assicurarsi di aver installato i requisiti.
2. Eseguire lo script di build:
   ```bash
   python build_exe.py
   ```
3. Troverai il file `AutoBackupPortable.exe` nella cartella `dist`. Questo file può essere copiato su una chiavetta USB ed eseguito su qualsiasi PC Windows senza installazione.
 
## Struttura del Progetto
 
- `main.py`: Interfaccia grafica e gestione del flusso (Wizard).
- `backup_engine.py`: Logica di core (scansione, copia, verifica).
- `build_exe.py`: Script per la creazione dell'eseguibile con PyInstaller.
