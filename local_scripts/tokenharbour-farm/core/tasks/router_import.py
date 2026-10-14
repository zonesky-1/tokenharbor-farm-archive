"""tasks.router_import — import API key ke 9router via import_tokenharbor.py.

Fitur bawaan script lama: deteksi duplikat (DB 9router), filter key
yang sudah terhubung, catat hasil di tokenharbor_imported.txt.
"""
from core import paths, prompts, runner, ui


def run():
    ui.header("📥 IMPORT KEY KE 9ROUTER")

    router_base = prompts.ask("URL 9router", default=paths.ROUTER_BASE_DEFAULT)
    prefix = prompts.ask("Prefix nama connection", default="ai")
    dry = prompts.ask_yes_no("Mode dry-run (preview tanpa POST)?", False)
    force = prompts.ask_yes_no(
        "Force re-import walau sudah pernah diimport?", False
    )

    args = [paths.SCRIPTS["import"], "--file", str(paths.KEYS_FILE),
            "--router-base", router_base, "--prefix", prefix]
    if dry:
        args.append("--dry-run")
    if force:
        args.append("--force")

    rc = runner.run_stream(args)
    if not dry:
        # tarik tokenharbor_imported.txt dari proyek induk ke output farm.
        # Dilakukan apa pun exit code-nya: bila import sukses sebagian lalu
        # script keluar error, jejak key yang sudah terimport tetap harus
        # tersimpan agar tidak terimport ganda nanti.
        from core import storage
        total, _baru = storage.merge_from_project()
        print(flush=True)
        print(f"  Jejak import disimpan di: {paths.IMPORTED_FILE}", flush=True)
        if rc == 0:
            print(f"  Cek kembali router di {router_base}", flush=True)
        else:
            print(f"  [!] Import tidak selesai sempurna (exit code {rc});", flush=True)
            print("      jalankan ulang menu [4] untuk melanjutkan.", flush=True)
