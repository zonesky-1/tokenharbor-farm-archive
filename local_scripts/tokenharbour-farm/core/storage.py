"""core.storage — baca, gabungkan, dan tampilkan akun milik FARM.

Output farm ada di <farm>/output/. Script lama (run_chrome.py dll.)
tetap menulis ke folder proyek induk; merge_from_project() menggabungkan
hasil terbaru dari sana ke output farm berdasarkan email — sehingga
update status dari verifikasi (yang menulis langsung ke output farm)
tidak tertimpa data basi dari induk.
"""
from core import paths, ui


def load_accounts(path=None):
    """Baca file keys -> list dict(email, password, key, status)."""
    path = path or paths.KEYS_FILE
    accounts = []
    if not path.exists():
        return accounts
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split("|")
        if len(parts) < 4:
            continue
        accounts.append({
            "email": parts[0].strip(),
            "password": parts[1].strip(),
            "key": parts[2].strip(),
            "status": parts[3].strip(),
        })
    return accounts


def _row_score(acc):
    """Skor kualitas baris: status 'ready' paling tinggi, lalu yang
    punya API key. Dipakai untuk memilih versi terbaik saat merge."""
    return (1 if acc["status"] == "ready" else 0,
            1 if acc["key"] else 0)


def _merge_lines_unique(existing, incoming):
    """Gabung daftar baris unik; urutan existing dipertahankan dulu."""
    seen = set(existing)
    merged = list(existing)
    for line in incoming:
        if line and line not in seen:
            seen.add(line)
            merged.append(line)
    return merged


def _read_lines(path):
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(
        encoding="utf-8-sig", errors="replace").splitlines() if l.strip()]


def merge_from_project():
    """Gabungkan hasil terbaru dari proyek induk ke output farm.

    - keys : merge per email, pilih versi terbaik (ready > ada key).
      Tie -> versi dari proyek induk (lebih baru).
    - ready/imported : gabung baris unik.

    Return (total_akun_output, jumlah_akun_baru_dari_induk).
    """
    paths.ensure_output_dir()

    # ── file sederhana: gabung baris unik ──
    for src, dst in ((paths.PROJECT_READY_FILE, paths.READY_FILE),
                     (paths.PROJECT_IMPORTED_FILE, paths.IMPORTED_FILE)):
        dst_lines = _read_lines(dst)
        merged = _merge_lines_unique(dst_lines, _read_lines(src))
        if merged != dst_lines:
            dst.write_text("\n".join(merged) + "\n", encoding="utf-8")

    # ── keys: merge per email ──
    proj = load_accounts(paths.PROJECT_KEYS_FILE)
    out = load_accounts(paths.KEYS_FILE)
    out_emails = {a["email"] for a in out}
    new_count = len([a for a in proj if a["email"] not in out_emails])

    by_email = {}
    order = []
    for a in out:                       # output farm = basis
        if a["email"] not in by_email:
            by_email[a["email"]] = a
            order.append(a["email"])
    for a in proj:                      # induk = kandidat pembaruan
        cur = by_email.get(a["email"])
        if cur is None:
            by_email[a["email"]] = a
            order.append(a["email"])
        elif _row_score(a) >= _row_score(cur):
            by_email[a["email"]] = a    # versi induk lebih baik / sama & lebih baru

    merged = [by_email[e] for e in order]
    new_text = "".join(
        f"{a['email']}|{a['password']}|{a['key']}|{a['status']}\n" for a in merged
    )
    old_text = (
        paths.KEYS_FILE.read_text(encoding="utf-8-sig", errors="replace")
        if paths.KEYS_FILE.exists() else ""
    )
    if new_text != old_text:            # hindari tulis ulang sia-sia
        paths.KEYS_FILE.write_text(new_text, encoding="utf-8")
    return len(merged), new_count


def show_accounts():
    """Tampilkan tabel akun + ringkasan status."""
    accounts = load_accounts()
    ui.header("📊 DAFTAR AKUN TOKEN HARBOR")
    if not accounts:
        print(f"  Belum ada akun di {paths.KEYS_FILE.name}", flush=True)
        print("  Jalankan menu [1] Farm akun baru terlebih dahulu.", flush=True)
        return
    rows = []
    for i, a in enumerate(accounts, start=1):
        key_disp = (a["key"][:24] + "...") if a["key"] else "-"
        rows.append((i, a["email"], a["status"], key_disp))
    ui.table(rows, ("No", "Email", "Status", "API Key"))

    print(flush=True)
    by_status = {}
    for a in accounts:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1
    print("  Ringkasan:", flush=True)
    for st, n in sorted(by_status.items()):
        print(f"    {st:12s}: {n}", flush=True)
    print(f"    {'TOTAL':12s}: {len(accounts)}", flush=True)
    print(flush=True)
    print(f"  File  : {paths.KEYS_FILE}", flush=True)
    print(f"  Ready : {paths.READY_FILE}", flush=True)
