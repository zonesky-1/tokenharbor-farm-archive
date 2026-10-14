"""tasks.free_models — aktifkan free models di tokenharbor.ai
via enable_free_models.py."""
from core import paths, prompts, runner, ui


def run():
    ui.header("🎁 ENABLE FREE MODELS")

    mode = prompts.ask_menu(
        "Akun mana yang diproses?",
        [
            ("failed", "Hanya akun yang sebelumnya gagal"),
            ("all", "Semua akun"),
            ("one", "Satu akun spesifik (input email)"),
        ],
        default="failed",
    )
    email = None
    if mode == "one":
        email = prompts.ask("Email akun", required=True)
    dry = prompts.ask_yes_no("Mode dry-run (preview saja)?", False)

    args = [paths.SCRIPTS["free_models"], "--file", str(paths.KEYS_FILE)]
    if mode == "all":
        args.append("--all")
    elif mode == "one":
        args += ["--email", email]
    if dry:
        args.append("--dry-run")

    runner.run_stream(args)
