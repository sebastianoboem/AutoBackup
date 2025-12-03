import os
import shutil
import psutil
import hashlib
import threading
import time
import platform
from pathlib import Path

class BackupEngine:
    def __init__(self):
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # Start unpaused
        self.current_status = "Ready"
        
        # Default Categories
        self.categories = {
            "Documenti": [".doc", ".docx", ".pdf", ".txt", ".xlsx", ".xls", ".pptx", ".ppt", ".odt"],
            "Immagini": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".raw", ".ico"],
            "Video": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
            "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma"],
            "Archivi": [".zip", ".rar", ".7z", ".tar", ".gz"]
        }
        
        if platform.system() == 'Darwin':
            self.system_folders = [
                "System", "Library", "Applications", "private", "usr", "var", 
                ".Spotlight-V100", ".fseventsd", "Volumes"
            ]
        else:
            self.system_folders = [
                "Windows", "Program Files", "Program Files (x86)", "ProgramData", 
                "$Recycle.Bin", "System Volume Information", "AppData",
                "Boot", "Recovery", "PerfLogs", "Config.Msi", "Documents and Settings",
                "MSOCache", "$WinREAgent", "OneDriveTemp", "Temp", "XboxGames", "WindowsApps", "Windows.old"
            ]

    def get_removable_drives(self):
        drives = []
        if platform.system() == 'Darwin':
            seen = set()
            for part in psutil.disk_partitions():
                if part.mountpoint.startswith('/Volumes/'):
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        key = part.mountpoint
                        if key in seen:
                            continue
                        seen.add(key)
                        drives.append({
                            'device': part.device,
                            'mountpoint': part.mountpoint,
                            'fstype': part.fstype,
                            'total': usage.total,
                            'free': usage.free
                        })
                    except Exception:
                        pass
            if not drives and os.path.isdir('/Volumes'):
                for name in os.listdir('/Volumes'):
                    mp = os.path.join('/Volumes', name)
                    if os.path.ismount(mp):
                        try:
                            usage = psutil.disk_usage(mp)
                            drives.append({
                                'device': mp,
                                'mountpoint': mp,
                                'fstype': '',
                                'total': usage.total,
                                'free': usage.free
                            })
                        except Exception:
                            pass
        else:
            for part in psutil.disk_partitions():
                if 'removable' in part.opts or part.opts == 'rw,removable':
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        drives.append({
                            'device': part.device,
                            'mountpoint': part.mountpoint,
                            'fstype': part.fstype,
                            'total': usage.total,
                            'free': usage.free
                        })
                    except Exception:
                        pass
        return drives

    def scan_files(self, source_drives, category_extensions_map, custom_extensions, exclusions, progress_callback=None):
        """
        Scans drives for files matching criteria.
        category_extensions_map: dict { "CategoryName": [".ext1", ".ext2"] }
        """
        files_to_copy = []
        total_size = 0
        
        # Compile allowed extensions and mapping
        allowed_exts = set()
        ext_to_cat = {}
        
        for cat, exts in category_extensions_map.items():
            for e in exts:
                allowed_exts.add(e)
                ext_to_cat[e] = cat
                
        for e in custom_extensions:
            allowed_exts.add(e)
            if e not in ext_to_cat:
                ext_to_cat[e] = "Altro"
                
        allowed_exts = {e.lower() for e in allowed_exts}

        for drive in source_drives:
            drive_path = Path(drive)
            root_label = ""
            if platform.system() == 'Darwin':
                p = drive_path.as_posix()
                if p.startswith('/Volumes/'):
                    parts = drive_path.parts
                    root_label = parts[2] if len(parts) > 2 else "Volume"
                else:
                    home = Path(os.path.expanduser("~"))
                    try:
                        if drive_path == home or str(drive_path).startswith(str(home)):
                            root_label = "Home"
                    except Exception:
                        root_label = ""
            else:
                root_label = drive_path.anchor.replace(":", "")
            
            # Special handling for System Drive (usually C:)
            # If scanning C: ROOT, strictly limit to C:\Users
            # If scanning a specific folder on C: (e.g. C:\Work), scan that folder.
            limit_to_user_profile = False
            
            if os.name == 'nt' and os.getenv('SystemDrive'):
                system_drive = os.getenv('SystemDrive').upper() # e.g. "C:"
                current_drive_root = drive_path.anchor.rstrip('\\/') # e.g. "C:"
                
                # Check if the path matches the system drive
                if current_drive_root.upper() == system_drive:
                    # Check if we are scanning the ROOT of the drive
                    # Comparison should be case-insensitive and ignore trailing slashes
                    abs_input = os.path.abspath(drive).rstrip('\\/').upper()
                    abs_root = os.path.abspath(drive_path.anchor).rstrip('\\/').upper()
                    
                    if abs_input == abs_root:
                        limit_to_user_profile = True
                    
            start_paths = [drive_path]
            if limit_to_user_profile:
                # On system drive ROOT, only scan CURRENT User folder
                # e.g. C:\Users\NomeUtente
                try:
                    user_path = Path(os.path.expanduser("~"))
                    # Verify this user path is actually on the drive we are scanning
                    if user_path.anchor.upper().rstrip('\\/') == current_drive_root.upper():
                        start_paths = [user_path]
                    else:
                        # Fallback: if user profile is not on system drive (rare setup), scan Users root
                        users_path = drive_path / "Users"
                        start_paths = [users_path] if users_path.exists() else [drive_path]
                except Exception:
                    # Fallback on error
                    users_path = drive_path / "Users"
                    start_paths = [users_path] if users_path.exists() else [drive_path]
            
            for start_path in start_paths:
                for root, dirs, files in os.walk(start_path):
                    # Check Stop/Pause
                    if self.stop_event.is_set():
                        return [], 0
                    
                    # 1. Prune subdirectories
                    dirs[:] = [d for d in dirs if not self._is_excluded(Path(root) / d, exclusions)]
                    
                    # 2. Check if CURRENT root is excluded
                    if self._is_excluded(Path(root), exclusions):
                        continue

                    for file in files:
                        try:
                            file_path = Path(root) / file
                            ext = file_path.suffix.lower()
                            
                            if ext in allowed_exts:
                                # Check size (might raise PermissionError)
                                stat = file_path.stat()
                                size = stat.st_size
                                category = ext_to_cat.get(ext, "Altro")
                                
                                files_to_copy.append({
                                    'source': str(file_path),
                                    'size': size,
                                    'category': category,
                                    'rel_path': str(file_path.relative_to(drive_path)),
                                    'root_label': root_label
                                })
                                total_size += size
                                
                                if progress_callback:
                                    progress_callback("scanning", file_path.name)
                        except Exception:
                            continue

        return files_to_copy, total_size

    def _is_excluded(self, path, exclusions):
        """Check if path matches any exclusion criteria."""
        path = Path(path)
        
        # Check hidden attribute (Windows) or dotfile (Unix/Windows)
        # Note: On Windows, checking FILE_ATTRIBUTE_HIDDEN is more robust, but stat().st_file_attributes is platform dependent.
        # For cross-platform simplicity, we check if any part starts with '.' (common convention)
        # AND on Windows specifically we can try to check the attribute if needed, but 'os.walk' doesn't give us attributes directly.
        # Let's implement a basic check: skip if name starts with '.' OR if we can detect hidden attribute.
        
        # 1. Check if any part of the path starts with '.' (covers .git, .venv, etc.) or '$' (system/hidden/temp)
        for part in path.parts:
            if part.startswith('.') or part.startswith('$'):
                return True

        # 2. Check Windows hidden attribute for the path itself (if it exists)
        if os.name == 'nt':
            try:
                import stat
                if path.exists():
                    attrs = path.stat().st_file_attributes
                    if attrs & stat.FILE_ATTRIBUTE_HIDDEN:
                        return True
            except Exception:
                pass

        # Check system folder names (exact match on parts)
        # Note: This is now handled via passed 'exclusions' list for flexibility, 
        # but we keep this check if user didn't override the list to be safe.
        # However, to allow user to Remove system folders from exclusion, we rely on the passed list.
        # If the passed list is empty, we might assume no exclusions, but usually it will contain at least defaults.
        # To be safe, we check if the exclusion list matches one of the system folders.
        
        # Check custom exclusions (path starts with exclusion)
        path_str = str(path).lower()
        for excl in exclusions:
            excl_str = str(excl).lower()
            # Check if exclusion is a direct parent or match
            # We use startswith on string representation for simple tree exclusion
            if path_str.startswith(excl_str):
                return True
                
            # Also check if a specific part matches the exclusion (for folder names like 'Windows' appearing anywhere)
            # But be careful: "Windows" exclusion should match C:\Windows, not C:\MyWindowsApp
            # The previous logic checked exact part matches for system folders.
            # We can try to emulate that if the exclusion doesn't look like a full path (no separators)
            if os.sep not in excl_str and '/' not in excl_str:
                 for part in path.parts:
                     if part.lower() == excl_str:
                         return True
                         
        return False

    def _get_category(self, ext):
        for cat, exts in self.categories.items():
            if ext in exts:
                return cat
        return "Altro"

    def copy_files(self, files_list, destination_root, verify=True, progress_callback=None):
        """
        Copies files to destination.
        Structure: Destination / Category / DriveLetter_Structure / ...
        """
        copied_count = 0
        copied_size = 0
        errors = []

        dest_path = Path(destination_root) / f"Backup_{int(time.time())}"
        dest_path.mkdir(parents=True, exist_ok=True)

        for file_info in files_list:
            # Check Pause
            self.pause_event.wait()
            
            # Check Stop
            if self.stop_event.is_set():
                break

            src = Path(file_info['source'])
            label = file_info.get('root_label', "")
            target_structure = Path(file_info['rel_path'])
            dst = dest_path / file_info['category'] / label / target_structure
            
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                
                if progress_callback:
                    progress_callback("copying", src.name, copied_size)

                shutil.copy2(src, dst)
                
                if verify:
                    if not self._verify_file(src, dst):
                        errors.append(f"Integrity check failed: {src}")
                
                copied_count += 1
                copied_size += file_info['size']
                
            except Exception as e:
                errors.append(f"Error copying {src}: {str(e)}")

        return copied_count, errors

    def _verify_file(self, src, dst):
        """Simple size check + optional hash check for critical verification."""
        # Fast check: Size
        if src.stat().st_size != dst.stat().st_size:
            return False
        # Deep check: MD5 (optional, can be slow for large files)
        # For this tool, we'll do a partial hash or full hash depending on requirements.
        # Let's do a full hash for safety as requested.
        return self._get_hash(src) == self._get_hash(dst)

    def _get_hash(self, path):
        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def stop(self):
        self.stop_event.set()
        self.pause_event.set() # Ensure we don't get stuck in pause

    def pause(self):
        self.pause_event.clear()

    def resume(self):
        self.pause_event.set()
