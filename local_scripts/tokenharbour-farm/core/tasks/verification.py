"""tasks.verification — verifikasi email akun yang belum verified.

Memanggil verify_tokenharbor_emails.py: cek status key (200/403),
login mail.tm, ambil link verifikasi, buka di Chrome, re-test key.
"""
from core import paths, prompts, runner, ui


def run():
    ui.header("✉️  VERIFIKASI EMAIL AKUN")

    scope = prompts.ask_menu(
        "Akun mana yang diverifikasi?",
        [
            ("unverified", "Hanya akun belum verified (key HTTP 403)"),
            ("all", "Semua akun"),
        ],
        default="unverified",
    )
    dry = prompts.ask_yes_no("Mode dry-run (preview saja, tanpa aksi)?", False)
    retest_router = prompts.ask_yes_no(
        "Re-test koneksi di 9router setelah key valid?", False
    )
    router_base = paths.ROUTER_BASE_DEFAULT
    if retest_router:
        router_base = prompts.ask(
            "URL 9router untuk re-test", default=paths.ROUTER_BASE_DEFAULT
        )

    args = [paths.SCRIPTS["verify"], "--file", str(paths.KEYS_FILE)]
    if scope == "all":
        args.append("--all")
    if retest_router:
        args += ["--retest-router", "--router-base", router_base]
    if dry:
        args.append("--dry-run")

    runner.run_stream(args)
