"""farm.py — TOKENHARBOUR FARM: program all-in-one interaktif.

Menggabungkan 5 program lama yang terpisah menjadi satu CLI
user-friendly: user cukup jalankan `start.bat`, lalu menjawab
pertanyaan yang muncul di layar.

Program lama TIDAK diubah — dipanggil via subprocess sebagai mesin
eksekusi yang sudah terbukti (lihat core/paths.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import paths, prompts, ui                      # noqa: E402
from core.tasks import (farming, free_models, keycheck,  # noqa: E402
                        router_import, verification)

MENU = [
    ("1", "🌾 Farm akun baru (daftar + verifikasi + key siap pakai)", farming.run),
    ("2", "✉️  Verifikasi email akun yang belum verified", verification.run),
    ("3", "🔑 Cek validitas API key semua akun", keycheck.run),
    ("4", "📥 Import key ke 9router", router_import.run),
    ("5", "🎁 Enable free models", free_models.run),
    ("6", "📊 Lihat daftar akun & status", None),
]


def main_menu():
    while True:
        ui.banner()
        print(flush=True)
        print("  Pilih tugas:", flush=True)
        for key, label, _fn in MENU:
            print(f"    {key}. {label}", flush=True)
        print("    0. Keluar", flush=True)
        print(flush=True)
        pilihan = input("  Ketik nomor [0-6]: ").strip()

        if pilihan == "0":
            print("  👋 Sampai jumpa!", flush=True)
            print("  Telegram: @Ortseam22 | Source asli: https://github.com/RanzMods/token-harbor", flush=True)
            break
        if pilihan == "6":
            ui.clear()
            from core import storage
            storage.show_accounts()
            prompts.pause()
            continue

        fn = next((f for k, _l, f in MENU if k == pilihan), None)
        if fn is None:
            print("  !! Pilihan tidak dikenal, ketik nomor 0-6.", flush=True)
            continue
        try:
            ui.clear()
            fn()
        except KeyboardInterrupt:
            print("\n  [!] Dibatalkan oleh user.", flush=True)
        except Exception as e:
            print(f"\n  [!!] Error: {type(e).__name__}: {e}", flush=True)
        try:
            prompts.pause()
        except EOFError:
            print(flush=True)
            break


def _frozen_run_child(passthrough):
    """Mode EXE: eksekusi script lama di dalam proses ini via runpy.

    Dipanggil ketika exe dijalankan ulang oleh runner dengan flag
    internal --th-run <script> <args...>. Script lama tetap utuh —
    hanya dijalankan, tidak dimodifikasi."""
    import runpy
    script = Path(passthrough[0]).resolve()
    sys.argv = [str(script)] + [str(a) for a in passthrough[1:]]
    sys.path.insert(0, str(script.parent))       # agar import saudara jalan
    try:
        runpy.run_path(str(script), run_name="__main__")
        return 0
    except SystemExit as e:
        code = e.code
        return code if isinstance(code, int) else 0


def main():
    missing = paths.missing_scripts()
    if missing:
        ui.banner()
        print(flush=True)
        print("  [!!] Script pendukung tidak ditemukan:", flush=True)
        for name in missing:
            print(f"    - {name}: {paths.SCRIPTS[name]}", flush=True)
        print("\n  Pastikan folder tokenharbour-farm berada di dalam", flush=True)
        print("  proyek token-harbor-main.", flush=True)
        try:
            prompts.pause()
        except EOFError:
            pass
        return 1
    paths.ensure_output_dir()
    try:
        main_menu()
    except (EOFError, KeyboardInterrupt):
        print("\n  👋 Sampai jumpa!", flush=True)
    return 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    _argv = sys.argv[1:]
    if _argv and _argv[0] == "--th-run":
        sys.exit(_frozen_run_child(_argv[1:]))
    sys.exit(main())
