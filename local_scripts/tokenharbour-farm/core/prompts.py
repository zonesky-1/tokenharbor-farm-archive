"""core.prompts — helper input interaktif untuk CLI user-friendly.

Semua pertanyaan punya default sehingga user cukup tekan Enter.
"""
def ask(text, default=None, required=False):
    """Tanya input teks. Return string (default jika user tekan Enter)."""
    while True:
        if default is not None:
            prompt = f"  {text} [{default}]: "
        else:
            prompt = f"  {text}: "
        val = input(prompt).strip()
        if not val and default is not None:
            return default
        if val or not required:
            return val
        print("  !! Input wajib diisi.", flush=True)


def ask_int(text, default=1, minimum=1, maximum=999):
    """Tanya angka dengan validasi rentang."""
    while True:
        raw = ask(text, str(default))
        try:
            val = int(raw)
        except ValueError:
            print(f"  !! Masukkan angka antara {minimum}-{maximum}.", flush=True)
            continue
        if val < minimum or val > maximum:
            print(f"  !! Angka harus antara {minimum}-{maximum}.", flush=True)
            continue
        return val


def ask_yes_no(text, default=False):
    """Tanya ya/tidak. Enter memakai default."""
    hint = "Y/n" if default else "y/N"
    while True:
        val = input(f"  {text} [{hint}]: ").strip().lower()
        if not val:
            return default
        if val in ("y", "yes", "ya"):
            return True
        if val in ("n", "no", "tidak"):
            return False
        print("  !! Jawab y atau n.", flush=True)


def ask_menu(title, options, default=None):
    """Tanya pilihan menu. options = list of (key, label).
    Return key yang dipilih."""
    print(f"\n  {title}", flush=True)
    for i, (key, label) in enumerate(options, start=1):
        marker = " *" if key == default else ""
        print(f"    {i}. {label}{marker}", flush=True)
    default_idx = None
    for i, (key, _l) in enumerate(options, start=1):
        if key == default:
            default_idx = i
            break
    while True:
        raw = input(f"  Pilih [1-{len(options)}"
                    f"{', Enter=' + str(default_idx) if default_idx else ''}]: ").strip()
        if not raw and default_idx:
            return options[default_idx - 1][0]
        try:
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1][0]
        except ValueError:
            pass
        print(f"  !! Pilih angka 1-{len(options)}.", flush=True)


def pause():
    """Jeda — tunggu Enter untuk kembali ke menu."""
    input("\n  [Tekan ENTER untuk kembali ke menu...]")
