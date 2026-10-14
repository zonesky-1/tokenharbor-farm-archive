"""tasks.farming — buat akun Token Harbor baru via pipeline run_chrome.py.

Pipeline: signup → validasi key → verifikasi email (inbox+Chrome bila
perlu) → recovery sign-in/key creation → simpan. Status 'ready' hanya
ditulis setelah konfirmasi HTTP 200.
"""
from core import paths, prompts, runner, storage, ui


def run():
    ui.header("🌾 FARM AKUN TOKEN HARBOR BARU")
    print("  Pipeline otomatis: daftar → verifikasi email → API key siap pakai.", flush=True)
    print(f"  Output farm : {paths.OUTPUT_DIR}", flush=True)
    print("  Estimasi ±8-10 menit per akun.", flush=True)
    print("  (Catatan: script lama menulis sementara di proyek induk,", flush=True)
    print("   hasil akan digabungkan otomatis ke folder output farm.)", flush=True)

    count = prompts.ask_int("Jumlah akun yang mau dibuat", default=1, minimum=1, maximum=100)
    label = prompts.ask("Label API key", default="router-prod")
    mode = prompts.ask_menu(
        "Mode jeda antar akun",
        [
            ("normal", "Normal — jeda 60 detik (paling aman)"),
            ("fast", "Fast — jeda 30 detik"),
            ("turbo", "Turbo — jeda 15 detik (risiko rate-limit)"),
        ],
        default="fast",
    )
    threads = 1
    if count > 1:
        threads = prompts.ask_int(
            "Proses paralel (threads)", default=1, minimum=1, maximum=min(count, 5)
        )
    proxy = prompts.ask_yes_no(
        "Gunakan web-proxy untuk hindari rate-limit per IP?", False
    )

    args = [paths.SCRIPTS["farming"], "--count", str(count), "--label", label]
    if mode == "fast":
        args.append("--fast")
    elif mode == "turbo":
        args.append("--turbo")
    if threads > 1:
        args += ["--threads", str(threads)]
    if proxy:
        args.append("--proxy")

    total_min = count * (9 if threads == 1 else max(3, 9 // threads))
    print(flush=True)
    if not prompts.ask_yes_no(
        f"Mulai farm {count} akun (estimasi ~{total_min} menit)?", True
    ):
        print("  Dibatalkan.", flush=True)
        return

    rc = runner.run_stream(args)
    if rc == 0:
        total, baru = storage.merge_from_project()
        ui.header("✅ HASIL FARMING")
        ready_lines = []
        if paths.READY_FILE.exists():
            ready_lines = [l.strip() for l in paths.READY_FILE.read_text(
                encoding="utf-8-sig", errors="replace").splitlines() if l.strip()]
        accounts = storage.load_accounts()
        fresh = [a for a in accounts if a["status"] == "ready"]
        print(f"  Akun baru dari sesi ini : {baru}", flush=True)
        print(f"  Akun status 'ready'     : {len(fresh)} (dari {len(accounts)} akun)", flush=True)
        print(f"  Total key tervalidasi   : {len(ready_lines)}", flush=True)
        print(flush=True)
        print(f"  Output farm : {paths.OUTPUT_DIR}", flush=True)
        print(flush=True)
        print("  Lanjutkan dengan menu [4] Import key ke 9router.", flush=True)
    else:
        print(flush=True)
        print("  Farming tidak selesai sempurna; mencoba menggabungkan", flush=True)
        print("  hasil parsial dari proyek induk ...", flush=True)
        total, baru = storage.merge_from_project()
        print(f"  Akun di output farm: {total} (baru: {baru})", flush=True)
