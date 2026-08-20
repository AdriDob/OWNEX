# Windows Desktop Persistence Architecture

## Current Implementation (v7.0.0)

### Database Location
- **Dev mode**: `./database/catseye.db` (repo-relative)
- **Frozen desktop bundle**: `%APPDATA%/OWNEX/database/catseye.db` (Windows) or `~/.config/OWNEX/database/catseye.db` (POSIX)

### Detection Logic
```python
def user_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = os.getenv("APPDATA") or os.getenv("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        return Path(base) / "OWNEX"
    return Path("data")
```

### WSL2 Backend Architecture
- Backend runs in WSL2 Ubuntu
- Database lives in WSL2 filesystem (repo directory)
- Windows launcher auto-detects WSL project path
- Data persists as long as WSL2 instance exists

## Data Flow

```
Windows User → OWNEX Launcher (PowerShell)
     ↓
WSL2 Ubuntu → start_backend.sh
     ↓
FastAPI Backend → SQLite DB (in WSL repo)
     ↓
Tauri Desktop Shell → Frontend → API
```

## Advantages
- **Zero-config**: No manual DB setup required
- **Auto-detection**: Launcher finds project dynamically
- **Backup-friendly**: Repo can be backed up/gitignored properly
- **Upgrade-safe**: Reinstalling OWNEX doesn't lose data (data in WSL, not Windows Program Files)

## Limitations
- **WSL dependency**: Data exists only in WSL2 filesystem
- **No Windows native storage**: DB not in %APPDATA%/OWNEX for WSL backend mode
- **Path sensitivity**: If WSL repo moves, data moves with it

## Future Improvements (Optional)
1. **Shared mount**: Mount Windows directory in WSL for cross-platform data access
2. **Sync mechanism**: Periodic sync between WSL DB and Windows backup
3. **Cloud backup**: Optional cloud sync for user data
4. **Migration tool**: Utility to move data between WSL locations

## Current Status
✅ **ADEQUATE** for Windows Desktop + WSL2 Backend architecture
✅ Data persists across OWNEX reinstalls (in WSL)
✅ Auto-detection works for arbitrary WSL usernames
✅ No manual configuration required

## Verification
- `database/db.py` has proper frozen detection
- `user_data_dir()` handles Windows APPDATA correctly
- `_ensure_db_dir()` creates directories before DB access
- Tested in dev mode (sqlite:///./database/catseye.db)
