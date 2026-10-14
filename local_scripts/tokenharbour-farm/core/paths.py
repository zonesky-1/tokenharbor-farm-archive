"""core.paths — lokasi direktori, script lama (referensi), dan file data.

Program lama TIDAK diubah sama sekali; modul ini hanya menunjuk lokasinya.

Mendukung dua mode:
- Normal  : dijalankan dari sumber (.py) — lokasi dihitung dari file ini.
- Frozen  : dijalankan sebagai EXE hasil PyInstaller — lokasi dihitung dari
  posisi exe, lalu folder proyek induk dicari otomatis ke atas (penanda:
  ada run_chrome.py) sehingga exe boleh ditaruh di sub-folder mana pun.
"""
import sys
from pathlib import Path

# ── mode frozen (EXE hasil PyInstaller)? ──
FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    FARM_DIR = Path(sys.executable).resolve().parent     # folder tempat exe
    _proj = next(
        (d for d in (FARM_DIR, *FARM_DIR.parents)
         if (d / "run_chrome.py").exists()),
        None,
    )
    PROJECT_DIR = _proj if _proj is not None else FARM_DIR.parent
else:
    FARM_DIR = Path(__file__).resolve().parent.parent      # tokenharbour-farm/
    PROJECT_DIR = FARM_DIR.parent                          # folder proyek induk
ROOT_DIR = PROJECT_DIR.parent                          # folder root repo

def _venv_python():
    """Cari interpreter venv pada beberapa lokasi umum (Windows & Unix)."""
    for base in (FARM_DIR, PROJECT_DIR, ROOT_DIR):
        for rel in (".venv/Scripts/python.exe", ".venv/bin/python"):
            p = base / rel
            if p.exists():
                return p
    return None

VENV_PYTHON = _venv_python()

# ── script lama yang jadi mesin eksekusi (dipanggil via subprocess) ──
SCRIPTS = {
    "farming": PROJECT_DIR / "run_chrome.py",
    "verify": PROJECT_DIR / "verify_tokenharbor_emails.py",
    "import": PROJECT_DIR / "import_tokenharbor.py",
    "free_models": PROJECT_DIR / "enable_free_models.py",
}

# ── output milik FARM (terpisah dari proyek induk) ──
OUTPUT_DIR = FARM_DIR / "output"
KEYS_FILE = OUTPUT_DIR / "tokenharbor_keys.txt"
READY_FILE = OUTPUT_DIR / "tokenharbor_ready.txt"
IMPORTED_FILE = OUTPUT_DIR / "tokenharbor_imported.txt"

# ── lokasi asli di proyek induk (ditulis oleh script lama; sumber merge) ──
PROJECT_KEYS_FILE = PROJECT_DIR / "tokenharbor_keys.txt"
PROJECT_READY_FILE = PROJECT_DIR / "tokenharbor_ready.txt"
PROJECT_IMPORTED_FILE = PROJECT_DIR / "tokenharbor_imported.txt"

ROUTER_BASE_DEFAULT = "http://localhost:20128"


def ensure_output_dir():
    """Pastikan folder output farm ada. Return path-nya."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def python_exe():
    """Path python dari venv; fallback ke python yang menjalankan farm."""
    if VENV_PYTHON is not None and VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def missing_scripts():
    """Daftar nama script lama yang tidak ditemukan."""
    return [name for name, p in SCRIPTS.items() if not p.exists()]
