import os
import sys
import subprocess
import psutil
import time
from backup_engine import BackupEngine
from colorama import init, Fore, Style
from tqdm import tqdm

# Initialize Colorama
init(autoreset=True)

class GumBackupApp:
    def __init__(self):
        self.engine = BackupEngine()
        self.selected_categories = []
        self.custom_extensions = []
        self.exclusions = []
        self.selected_drive = None
        self.gum_exe = self._find_gum()
        self.test_mode = False
        self.active_category_map = {}
        self.extra_folders = []
        self.whitelist_paths = [os.path.expanduser("~")] # Default to user home

    def _find_gum(self):
        # Check if running from PyInstaller bundle
        if hasattr(sys, '_MEIPASS'):
            bundled_gum = os.path.join(sys._MEIPASS, "gum.exe")
            if os.path.exists(bundled_gum):
                return bundled_gum
        
        # Check current directory
        local_gum = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gum.exe")
        if os.path.exists(local_gum):
            return local_gum
            
        # Check PATH (assuming 'gum' is in path)
        if shutil.which("gum"):
            return "gum"
            
        return None

    def _run_gum(self, args, input_text=None):
        if not self.gum_exe:
            print(Fore.RED + "Errore: gum.exe non trovato! Assicurati che sia nella cartella del programma.")
            sys.exit(1)
            
        cmd = [self.gum_exe] + args
        try:
            # We capture stdout to get the result (selection/text)
            # We DO NOT capture stderr so the interactive UI is shown to the user
            # We DO NOT capture stdin unless we are passing input_text
            
            kwargs = {
                'stdout': subprocess.PIPE,
                'text': True,
                'encoding': 'utf-8',
                'check': False
            }
            
            if input_text is not None:
                kwargs['input'] = input_text
            
            result = subprocess.run(cmd, **kwargs)
            return result
        except Exception as e:
            print(Fore.RED + f"Errore esecuzione gum: {e}")
            sys.exit(1)

    def clear_screen(self):
        # Try using gum clear for better compatibility if available
        if self.gum_exe:
             # subprocess.run([self.gum_exe, "clear"]) # gum doesn't have clear, but we can just use system clear
             # Actually standard clear is fine, but let's ensure it fully clears scrollback if possible
             # or just rely on system cls/clear which is standard.
             os.system('cls' if os.name == 'nt' else 'clear')
        else:
             os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self, title):
        self.clear_screen()
        # Use gum style if possible, otherwise fallback
        if self.gum_exe:
            self._run_gum(["style", "--foreground", "212", "--border", "double", "--padding", "0 1", "--margin", "1", f"AutoBackup (Gum) - {title}"])
        else:
            print(Fore.MAGENTA + Style.BRIGHT + f"--- AutoBackup (Gum) - {title} ---")

    def step0_test_mode(self):
        self.print_header("Modalità Test")
        
        # Gum confirm for test mode
        res = self._run_gum(["confirm", "Abilitare la modalità TEST (limitata a 10 file per tipo)?"])
        if res.returncode == 0:
            self.test_mode = True
            print(Fore.YELLOW + "MODALITÀ TEST ATTIVATA: Verranno copiati max 10 file per categoria.")
            time.sleep(1)
        else:
            self.test_mode = False

    def step1_select_filters(self):
        self.print_header("Filtri File")
        
        cats = list(self.engine.categories.keys())
        
        # Default selection: Documenti, Immagini, Video
        default_selected = ["Documenti", "Immagini", "Video"]
        
        print(Fore.CYAN + "Seleziona le categorie da includere:")
        
        # Gum choose for categories
        # --no-limit allows multiple selection
        # --cursor="-> " format to avoid issue where "-> " is interpreted as a flag
        # --selected sets the default checked items
        res = self._run_gum([
            "choose", 
            "--no-limit", 
            "--height", "15", 
            "--cursor=-> ", 
            "--selected", ",".join(default_selected)
        ] + cats)
        
        if res.returncode != 0:
            sys.exit()
            
        self.selected_categories = [x for x in res.stdout.strip().split('\n') if x]
        
        if not self.selected_categories:
            print(Fore.RED + "\nNessuna categoria selezionata.")
            time.sleep(1)
            sys.exit()

        # --- NEW: Select specific extensions PER CATEGORY ---
        # We iterate through each selected category and ask the user to refine extensions for that category.
        self.active_category_map = {}
        
        # Extensions to be deselected by default
        default_deselected_exts = [
            ".txt", ".gif", ".bmp", ".tiff", ".raw", ".ico", 
            ".mkv", ".flv", ".flac", ".ogg", ".aac", ".tar", ".gz"
        ]
        
        for cat in self.selected_categories:
            self.clear_screen() # Clear screen before showing extra folders info to avoid clutter from previous steps
            exts = sorted(self.engine.categories[cat])
            
            # Skip if no extensions (shouldn't happen)
            if not exts:
                continue
                
            # Determine which extensions are selected by default
            # Select ALL minus the ones in default_deselected_exts
            pre_selected = [e for e in exts if e not in default_deselected_exts]
                
            # self.print_header(f"Filtro Estensioni per {cat}:")
            print(Fore.CYAN + f"Filtro Estensioni per {cat}:")
            print(Fore.CYAN + "Seleziona le estensioni che vuoi copiare")
            
            # Gum choose for extensions of this category
            # Note: gum choose --selected expects a comma-separated list of values to be pre-selected
            
            gum_args = [
                "choose", 
                "--no-limit", 
                "--height", "10", 
                "--cursor=-> ", 
                "--header=", # Empty header because we printed it manually above
            ]
            
            if pre_selected:
                gum_args.extend(["--selected", ",".join(pre_selected)])
                
            gum_args.extend(exts)
            
            res = self._run_gum(gum_args)
            
            if res.returncode != 0:
                sys.exit()
                
            selected_exts_list = [x for x in res.stdout.strip().split('\n') if x]
            
            if selected_exts_list:
                self.active_category_map[cat] = selected_exts_list
            else:
                print(Fore.YELLOW + f"Nessuna estensione selezionata per {cat}. La categoria verrà ignorata.")
                time.sleep(1)

        # Check if we have any categories left active
        if not self.active_category_map:
             print(Fore.RED + "\nNessuna categoria/estensione attiva selezionata.")
             time.sleep(2)
             sys.exit()

        # Custom Extensions
        # Gum confirm: default is "No" (return code 1), so we invert logic or check specifically.
        self.clear_screen() # Clear screen before showing extra folders info to avoid clutter from previous steps
        
        res = self._run_gum(["confirm", "--default=false", "Vuoi aggiungere estensioni personalizzate?"])
        if res.returncode == 0: # 0 = Yes
            res_input = self._run_gum(["input", "--placeholder", "es. .log, .dat"])
            exts = res_input.stdout.strip()
            if exts:
                self.custom_extensions = [e.strip() for e in exts.split(",") if e.strip()]

        # --- NEW: Whitelist Paths ---
        # Replaces "Extra Folders" and "Auto-included" display
        # Note: self.whitelist_paths is initialized with user home in __init__
        self.clear_screen()
        
        print(Fore.CYAN + "Definizione Percorsi di Ricerca")
        print(Fore.CYAN + "Default: Ricerca automatica su tutti i dischi fissi.")
        print(Fore.CYAN + "Opzionale: Puoi specificare una lista di cartelle precise (Whitelist).")
        
        if self.whitelist_paths:
             print(Fore.YELLOW + "\nWhitelist attuale:")
             for p in self.whitelist_paths:
                 print(Fore.YELLOW + f"   - {p}")
        else:
             print(Fore.YELLOW + "\nWhitelist attuale: (Nessuna - Scansione Completa)")
             
        print("")
        
        res = self._run_gum(["confirm", "--default=false", "Vuoi modificare la lista delle cartelle esclusive?"])
        if res.returncode == 0:
             print(Fore.CYAN + "\nInserisci i percorsi da scansionare (uno per riga).")
             print(Fore.CYAN + "Premi CTRL+D (o CTRL+Z su Windows) poi INVIO per terminare.")
             
             # Pre-fill if existing
             current_value = "\n".join(self.whitelist_paths) if self.whitelist_paths else ""
             
             res_write = self._run_gum(["write", "--value", current_value, "--placeholder", "Esempio:\nC:\\Dati_Importanti\nD:\\Foto_Vacanze"])
             
             if res_write.returncode == 0:
                 paths = res_write.stdout.strip().split('\n')
                 self.whitelist_paths = [] # Reset
                 for p in paths:
                     clean_p = p.strip()
                     if clean_p:
                         if os.path.exists(clean_p) and os.path.isdir(clean_p):
                            self.whitelist_paths.append(clean_p)
                         else:
                            print(Fore.YELLOW + f"Attenzione: '{clean_p}' non esiste o non è una cartella.")
                            time.sleep(1)
                            
             if self.whitelist_paths:
                  print(Fore.GREEN + f"MODALITÀ WHITELIST ATTIVA: {len(self.whitelist_paths)} percorsi definiti.")
                  time.sleep(1)
             else:
                  print(Fore.YELLOW + "Nessun percorso valido inserito. Si userà la ricerca standard (tutti i dischi).")
                  time.sleep(2)

        # --- NEW: Extra Exclusions to Add ---
        self.clear_screen()
        
        # Initialize exclusions with defaults if empty
        if not self.exclusions:
            self.exclusions = list(self.engine.system_folders)

        # Show current auto-excluded paths (System folders + Dot folders)
        print(Fore.CYAN + "Gestione Esclusioni")
        print(Fore.CYAN + "Definisci quali cartelle ignorare.")
        print(Fore.RED + "   - Cartelle nascoste (es. .git, .venv, $Recycle.Bin) sono SEMPRE escluse.")
        
        # Show preview of current exclusions
        print(Fore.YELLOW + "\nEsclusioni attuali (Default):")
        for excl in self.exclusions:
            print(Fore.YELLOW + f"   - {excl}")
        print("") # spacing

        # Ask if user wants to add extra exclusions
        res = self._run_gum(["confirm", "--default=false", "Vuoi modificare la lista delle esclusioni?"])
        if res.returncode == 0:
            print(Fore.CYAN + "\nModifica i percorsi da escludere (uno per riga).")
            print(Fore.CYAN + "Premi CTRL+D (o CTRL+Z su Windows) poi INVIO per salvare.")
             
            # Pre-fill with current exclusions (defaults + custom)
            current_value = "\n".join(self.exclusions)
            
            res_write = self._run_gum(["write", "--value", current_value, "--width", "80", "--height", "15"])
             
            if res_write.returncode == 0:
                paths = res_write.stdout.strip().split('\n')
                self.exclusions = [] # Reset and rebuild from user input
                for p in paths:
                    clean_p = p.strip()
                    if clean_p:
                        self.exclusions.append(clean_p)
             
        if self.exclusions:
            print(Fore.GREEN + f"Lista esclusioni aggiornata: {len(self.exclusions)} regole attive.")
            time.sleep(1)

    def step2_select_drive(self):
        self.print_header("Destinazione")
        
        while True:
            drives = self.engine.get_removable_drives()
            
            if not drives:
                print(Fore.RED + "Nessuna unità USB trovata!")
                res = self._run_gum(["confirm", "Riprovare?"])
                if res.returncode != 0:
                    sys.exit()
                continue
            
            # Prepare choices for gum
            drive_map = {}
            choices = []
            for d in drives:
                label = f"{d['mountpoint']} [{d['device']}] ({d['free']//(1024**3)} GB Free)"
                drive_map[label] = d
                choices.append(label)
            
            choices.append("Aggiorna Lista")
            
            res = self._run_gum(["choose", "--header", "Scegli l'unità di destinazione"] + choices)
            selection = res.stdout.strip()
            
            if not selection:
                sys.exit()
                
            if selection == "Aggiorna Lista":
                continue
                
            self.selected_drive = drive_map[selection]
            break

    def step3_scan_and_confirm(self):
        self.print_header("Scansione")
        
        # Use the filtered map instead of raw categories
        cat_map = self.active_category_map
        
        # Logic for scan roots
        all_scan_roots = []
        
        # 1. Identify all fixed drives
        fixed_drives = []
        for part in psutil.disk_partitions():
            if 'fixed' in part.opts or 'rw,fixed' in part.opts:
                 fixed_drives.append(part.mountpoint)
        
        # Remove destination drive if it's in the list (to avoid recursion)
        dest_mount = self.selected_drive['mountpoint']
        if dest_mount in fixed_drives:
            fixed_drives.remove(dest_mount)
            
        # 2. Apply Whitelist Logic PER DRIVE
        # Algorithm:
        # Iterate through each fixed drive.
        # Check if there are any whitelist paths that belong to this drive.
        # IF YES: Add ONLY those whitelist paths for this drive.
        # IF NO: Add the entire drive root.
        
        # Helper to check if path is on drive
        def is_on_drive(path, drive_root):
            try:
                # Normalize paths
                p_abs = os.path.abspath(path).lower()
                d_abs = os.path.abspath(drive_root).lower()
                # Drive root usually ends with backslash (C:\), but if not we ensure it
                if not d_abs.endswith(os.sep):
                    d_abs += os.sep
                return p_abs.startswith(d_abs)
            except:
                return False
                
        used_whitelist_paths = []
        
        for drive in fixed_drives:
            # Find whitelist entries for this drive
            drive_specific_paths = []
            if self.whitelist_paths:
                for wp in self.whitelist_paths:
                    if is_on_drive(wp, drive):
                        drive_specific_paths.append(wp)
            
            if drive_specific_paths:
                # Whitelist applies for this drive: Scan ONLY specific paths
                all_scan_roots.extend(drive_specific_paths)
                used_whitelist_paths.extend(drive_specific_paths)
            else:
                # No whitelist for this drive: Scan FULL drive
                all_scan_roots.append(drive)
        
        # Also add any whitelist paths that might not match a fixed drive (e.g. network shares if supported later, or edge cases)
        # But for now, if a user added a path that wasn't detected as part of a fixed drive, we should probably add it anyway to be safe.
        for wp in self.whitelist_paths:
            if wp not in used_whitelist_paths:
                all_scan_roots.append(wp)

        # --- RESOCONTO PRE-SCANSIONE ---
        self.print_header("Resoconto Configurazioni")
        
        print(Fore.CYAN + "Stai per avviare la ricerca con queste impostazioni:\n")
        
        print(Fore.WHITE + Style.BRIGHT + "Modalità:")
        print(f"   - Test Mode: {'ATTIVA (Max 10 file)' if self.test_mode else 'Disattivata (Copia completa)'}")
        if self.whitelist_paths:
             print(f"   - Strategia Scansione: MISTA (Whitelist per drive / Full per gli altri)")
        else:
             print(f"   - Strategia Scansione: COMPLETA (Tutti i dischi fissi)")
        
        print(Fore.WHITE + Style.BRIGHT + "\nDestinazione:")
        print(f"   - Unità: {self.selected_drive['mountpoint']} [{self.selected_drive['device']}]")
        print(f"   - Spazio Libero: {self.selected_drive['free']//(1024**3)} GB")
        
        print(Fore.WHITE + Style.BRIGHT + "\nPercorsi di Scansione Effettivi:")
        for root in all_scan_roots:
            # Check if it's a full drive or a specific folder for display
            is_drive_root = False
            if os.name == 'nt':
                 if len(root) <= 3 and root.endswith(':\\'): is_drive_root = True
            
            if is_drive_root:
                print(Fore.GREEN + f"   - {root} (Intero Disco)")
            else:
                print(Fore.GREEN + f"   - {root} (Cartella Specifica)")

        if self.extra_folders: # Legacy check, though extra_folders is removed from UI, kept for safety
             for f in self.extra_folders:
                 print(Fore.GREEN + f"   - {os.path.abspath(f)}")
            
        print(Fore.WHITE + Style.BRIGHT + "\nPercorsi ESCLUSI:")
        
        # Deduplicate for display
        # If exclusions list is empty (default), we show system folders.
        # If user modified it, we show what is in self.exclusions.
        # We categorize them for clarity.
        
        display_exclusions = self.exclusions if self.exclusions else self.engine.system_folders
        
        # Separate system defaults from custom additions for cleaner display
        system_excl_display = []
        custom_excl_display = []
        
        for excl in display_exclusions:
             if excl in self.engine.system_folders:
                 system_excl_display.append(excl)
             else:
                 custom_excl_display.append(excl)
                 
        if system_excl_display:
             print(Fore.RED + "   - [Sistema] Cartelle di sistema:")
             for f in system_excl_display:
                  print(Fore.RED + f"     * {f}")
                  
        if custom_excl_display:
            print(Fore.RED + "   - [Custom] Utente:")
            for e in custom_excl_display:
                 print(Fore.RED + f"     * {e}")
                 
        print(Fore.RED + "   - [Auto] Tutte le cartelle che iniziano con '.' (es. .git) o '$' (es. $Recycle.Bin)")
            
        print(Fore.WHITE + Style.BRIGHT + "\nFiltri Attivi:")
        for cat, exts in cat_map.items():
            print(f"   - {cat}: {', '.join(exts)}")
        
        if self.custom_extensions:
            print(f"   - Custom: {', '.join(self.custom_extensions)}")
            
        print("\n" + "-"*50 + "\n")
        
        # Gum confirm to proceed
        res = self._run_gum(["confirm", "Controlla se le impostazioni sono corrette.\nProcedere con la scansione?"])
        if res.returncode != 0:
            print(Fore.RED + "Operazione annullata dall'utente.")
            sys.exit()

        print(Fore.YELLOW + "Avvio analisi file in corso...")
        
        files, size = self.engine.scan_files(all_scan_roots, cat_map, self.custom_extensions, self.exclusions)
        
        if self.test_mode:
            print(Fore.YELLOW + "Applicazione filtro TEST MODE (max 10 file per categoria)...")
            filtered_files = []
            cat_counts = {}
            new_size = 0
            
            for f in files:
                cat = f['category']
                count = cat_counts.get(cat, 0)
                if count < 10:
                    filtered_files.append(f)
                    cat_counts[cat] = count + 1
                    new_size += f['size']
            
            files = filtered_files
            size = new_size

        self.print_header("Riepilogo")
        if self.test_mode:
            print(Fore.YELLOW + "[TEST MODE ATTIVA]")
            
        print(Fore.GREEN + f"Risultati Scansione:")
        print(f"  - File trovati: {len(files)}")
        print(f"  - Dimensione totale: {size / (1024*1024):.2f} MB")
        
        if not files:
            print(Fore.RED + "\nNessun file trovato.")
            sys.exit()

        res = self._run_gum(["confirm", "Procedere con il backup?"])
        if res.returncode != 0:
            sys.exit()
        
        return files, size

    def step4_perform_backup(self, files, total_size):
        self.print_header("Backup in corso")
        dest = self.selected_drive['mountpoint']
        
        pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc="Copia", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
        
        def progress_callback(action, filename, current_copied_size=0):
            delta = current_copied_size - pbar.n
            if delta > 0:
                pbar.update(delta)

        try:
            count, errors = self.engine.copy_files(files, dest, progress_callback=progress_callback)
            pbar.close()
            
            self.print_header("Completato")
            
            # Use gum style for success message
            self._run_gum(["style", "--foreground", "212", "--border", "rounded", "--align", "center", "--width", "50", f"Backup Completato!\n{count} file copiati."])
            
            if errors:
                print(Fore.RED + f"Si sono verificati {len(errors)} errori. Vedi 'backup_errors.log'")
                with open("backup_errors.log", "w") as f:
                    for e in errors: f.write(e + "\n")
            
            print("\nPremi INVIO per uscire...")
            input() # simple input to wait
                
        except KeyboardInterrupt:
            print(Fore.RED + "\n\nInterrotto!")
            self.engine.stop()

    def run(self):
        try:
            self.step0_test_mode()
            self.step1_select_filters()
            self.step2_select_drive()
            files, size = self.step3_scan_and_confirm()
            self.step4_perform_backup(files, size)
        except KeyboardInterrupt:
            print("\nUscita.")

if __name__ == "__main__":
    import shutil
    app = GumBackupApp()
    app.run()
