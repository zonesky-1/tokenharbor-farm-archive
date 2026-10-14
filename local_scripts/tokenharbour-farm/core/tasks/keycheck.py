"""tasks.keycheck — cek validitas API key semua akun langsung ke API.

Read-only: tidak mengubah file keys. Key dites GET /v1/models;
200 = valid, 403 = unverified, lainnya = invalid/error.
"""
from core import paths, storage, ui

API_MODELS_URL = "https://tokenharbor.ai/v1/models"
TIMEOUT = 30


def check_key(key):
    """Return (http_status, keterangan)."""
    try:
        # import di dalam fungsi agar farm tetap jalan walau requests
        # belum terpasang (bug crash saat startup bila import global)
        import requests
    except ImportError:
        return -1, "MODUL requests TIDAK ADA (install: pip install requests)"
    try:
        r = requests.get(
            API_MODELS_URL,
            headers={"Authorization": f"Bearer {key}"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return 200, "VALID ✓"
        if r.status_code == 403:
            return 403, "UNVERIFIED (perlu verifikasi email)"
        return r.status_code, "INVALID / ERROR"
    except requests.RequestException as e:
        return -1, f"GAGAL KONEKSI ({type(e).__name__})"


def run():
    ui.header("🔑 CEK VALIDITAS API KEY")
    accounts = storage.load_accounts()
    with_key = [a for a in accounts if a["key"]]
    if not with_key:
        print("  Tidak ada API key untuk dites.", flush=True)
        print("  Jalankan menu [1] Farm akun baru terlebih dahulu.", flush=True)
        return

    print(f"  Menguji {len(with_key)} key ke {API_MODELS_URL} ...", flush=True)
    rows = []
    counts = {"valid": 0, "unverified": 0, "invalid": 0}
    for i, a in enumerate(with_key, start=1):
        code, ket = check_key(a["key"])
        if code == 200:
            counts["valid"] += 1
        elif code == 403:
            counts["unverified"] += 1
        else:
            counts["invalid"] += 1
        rows.append((i, a["email"], code, ket))
        print(f"    [{i}/{len(with_key)}] {a['email']} -> {code}", flush=True)

    ui.header("📋 HASIL PENGECEKAN")
    ui.table(rows, ("No", "Email", "HTTP", "Status"))
    print(flush=True)
    print(f"  Valid     : {counts['valid']}", flush=True)
    print(f"  Unverified: {counts['unverified']}  (jalankan menu [2] Verifikasi email)", flush=True)
    print(f"  Invalid   : {counts['invalid']}", flush=True)
    if counts["valid"]:
        print(flush=True)
        print("  Lanjutkan dengan menu [4] Import key ke 9router.", flush=True)
