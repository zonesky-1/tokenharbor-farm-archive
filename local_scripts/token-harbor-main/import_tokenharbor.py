#!/usr/bin/env python3
"""import_tokenharbor.py — import semua API key Token Harbor dari file txt
ke server 9router, ditumpuk ke provider yang memakai API https://tokenharbor.ai/v1.

Cara kerja:
  1) baca key thk_live_... dari tokenharbor_keys.txt (kolom ke-3, status "ok")
  2) auto-detect di 9router (GET /api/providers) provider/connection yang
     providerSpecificData.baseUrl == https://tokenharbor.ai/v1
  3) POST tiap key ke /api/providers dengan provider id yang sama
     (server otomatis mengisi baseUrl/prefix/nodeName dari node provider),
     authType=apikey, priority bertambah (stacking), testStatus=unknown
  4) NAMA UNIK: 9router meng-upsert berdasarkan name. Bila nama (mis. "ai 1")
     sudah terpakai, script otomatis membuat nama random baru (mis. "ai 1-x7k2")
     sehingga key baru SELALU menambah connection baru, tidak menimpa yang lama.
  5) DETEKSI DUP IKAT: script membaca database sqlite 9router dan membatalkan
     key yang SUDAH terhubung (key sama dengan connection yang ada) — key tsb
     tidak di-POST sama sekali.
  6) catat key yang sudah di-import di tokenharbor_imported.txt agar tidak
     dobel saat dijalankan ulang

Cara pakai:
  python3 import_tokenharbor.py                  # import semua key baru
  python3 import_tokenharbor.py --dry-run        # hanya preview, tidak POST
  python3 import_tokenharbor.py --force          # import ulang walau sudah pernah
  python3 import_tokenharbor.py --provider <id>  # tentukan provider manual
  python3 import_tokenharbor.py --prefix ai --start-priority 3
  python3 import_tokenharbor.py --file tokenharbor_keys.txt
  python3 import_tokenharbor.py --db /path/data.sqlite  # lokasi DB manual
  python3 import_tokenharbor.py --no-db-check          # lewati deteksi duplikat
"""

import argparse
import hashlib
import json
import os
import random
import re
import sqlite3
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grok  # noqa: E402
import requests  # noqa: E402

BASE_URL = "https://tokenharbor.ai/v1"
KEY_RE = re.compile(r"\bthk_live_[A-Za-z0-9_-]{20,}\b")
KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokenharbor_keys.txt")
IMPORTED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokenharbor_imported.txt")
DB_PATHS = [
    os.path.join(os.path.expanduser("~/.9router"), "db", "data.sqlite"),
    os.path.join(os.path.expanduser("~/.9router"), "data.sqlite"),
    os.path.join(os.environ.get("DATA_DIR", ""), "db", "data.sqlite") if os.environ.get("DATA_DIR") else None,
    "/var/lib/9router/db/data.sqlite",
]


def load_keys(path):
    """Baca email|password|apikey|status dari file txt. Return list (email, key)."""
    out = []
    if not os.path.exists(path):
        print(f"✗ file tidak ada: {path}")
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            key = ""
            status = ""
            email = parts[0].strip() if parts else ""
            for p in parts[1:]:
                m = KEY_RE.search(p)
                if m:
                    key = m.group(0)
            if len(parts) >= 4:
                status = parts[3].strip()
            elif not key and len(parts) >= 2 and KEY_RE.search(line):
                status = "ok"
            if key and status == "ok":
                out.append((email, key))
    # dedupe key
    seen, uniq = set(), []
    for e, k in out:
        if k not in seen:
            seen.add(k)
            uniq.append((e, k))
    return uniq


def _md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def load_imported():
    if not os.path.exists(IMPORTED_FILE):
        return set()
    with open(IMPORTED_FILE, encoding="utf-8") as f:
        return {ln.strip() for ln in f if ln.strip()}


def mark_imported(key):
    with open(IMPORTED_FILE, "a", encoding="utf-8") as f:
        f.write(_md5(key) + "\n")


def get_connected_keys(db_path=None):
    """Ambil semua apiKey yang SUDAH terhubung ke 9router.

    Dibaca langsung dari database sqlite 9router (tabel providerConnections,
    kolom data JSON berisi apiKey). GET /api/providers tidak mengembalikan
    apiKey (di-void oleh server), jadi DB adalah sumber kebenaran.

    Return set apiKey. Bila DB tidak terbaca, return None (tidak bisa deteksi).
    """
    candidates = [db_path] if db_path else DB_PATHS
    for p in candidates:
        if not p or not os.path.exists(p):
            continue
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            rows = con.execute("SELECT data FROM providerConnections").fetchall()
            con.close()
            keys = set()
            for (d,) in rows:
                if not d:
                    continue
                try:
                    obj = json.loads(d)
                except Exception:
                    continue
                k = obj.get("apiKey")
                if k and isinstance(k, str):
                    keys.add(k)
            if keys or rows:
                return keys
        except Exception:
            continue
    return None


def get_providers(router_base, token):
    resp = requests.get(
        f"{router_base}/api/providers",
        cookies={"auth_token": token},
        headers={"Accept": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("connections", [])


def _unique_suffix():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=4))


def unique_name(base, used_names):
    """Return nama yang pasti belum terpakai.

    Kalau `base` (mis. "ai 1") sudah ada di 9router, ditambah suffix random
    (mis. "ai 1-x7k2") sampai unik. Ini mencegah 9router meng-upsert key baru
    ke connection nama yang sama (yang membuat jumlah akun tidak bertambah).
    """
    name = base
    while name in used_names:
        name = f"{base}-{_unique_suffix()}"
    return name


def find_target_provider(providers, provider_id=None):
    """Pilih provider template id yang dipakai oleh koneksi tokenharbor.ai/v1.

    - provider_id diberikan -> pakai itu (validasi: harus ada node/connection).
    - otomatis -> cari connection yang providerSpecificData.baseUrl cocok
      https://tokenharbor.ai/v1, ambil provider id-nya (yang paling sering dipakai).
    Return (provider_id, contoh_koneksi_untuk_default_model, max_priority).
    """
    cands = []
    for c in providers:
        data = c.get("providerSpecificData") or {}
        url = (data.get("baseUrl") or "").strip().rstrip("/")
        if url == BASE_URL.rstrip("/"):
            cands.append(c)

    if provider_id:
        known = [c for c in cands if c.get("provider") == provider_id]
        if not known:
            print(f"✗ provider '{provider_id}' tidak punya koneksi tokenharbor.ai/v1 di 9router.")
            print("  Daftar provider yang tersedia dengan baseUrl tsb:")
            for c in cands:
                print(f"    - {c.get('provider')}  name={c.get('name')}")
            sys.exit(1)
        target = provider_id
    else:
        if not cands:
            print(f"✗ Tidak ada koneksi di 9router dengan baseUrl '{BASE_URL}'.")
            print("  Tambahkan dulu provider OpenAI-compatible dengan baseUrl tsb "
                  "lewat dashboard, lalu jalankan ulang.")
            sys.exit(1)
        # pilih provider id dengan jumlah koneksi terbanyak (paling dipakai)
        from collections import Counter
        cnt = Counter(c.get("provider") for c in cands)
        target = cnt.most_common(1)[0][0]

    example = next((c for c in cands if c.get("provider") == target), cands[0])
    default_model = example.get("defaultModel") or "gpt-4o-mini"
    max_pri = max((c.get("priority") or 1) for c in cands if c.get("provider") == target) or 0
    return target, default_model, max_pri


def main():
    ap = argparse.ArgumentParser(description="Import API key Token Harbor ke 9router (stacking)")
    ap.add_argument("--file", default=KEYS_FILE, help="file txt berisi key (default tokenharbor_keys.txt)")
    ap.add_argument("--router-base", default=grok.ROUTER_BASE, help="base URL 9router")
    ap.add_argument("--provider", default=None, help="provider template id (auto-detect bila kosong)")
    ap.add_argument("--prefix", default="ai", help="prefix nama connection (default 'ai')")
    ap.add_argument("--start-priority", type=int, default=None,
                    help="priority awal (default: max priority existing + 1)")
    ap.add_argument("--default-model", default=None, help="defaultModel (default dari koneksi existing)")
    ap.add_argument("--force", action="store_true", help="import ulang walau sudah pernah")
    ap.add_argument("--dry-run", action="store_true", help="preview saja, tidak POST")
    ap.add_argument("--db", default=None,
                    help="path sqlite 9router (default auto-detect). Kosongkan DB "
                         "bila tak terbaca -> deteksi duplikat dilewati.")
    ap.add_argument("--no-db-check", action="store_true",
                    help="nonaktifkan deteksi key yang sudah terhubung via DB")
    ap.add_argument("--auto-import", action="store_true", 
                    help="auto-import setelah verifikasi email (jalankan verify_tokenharbor_emails.py dulu)")
    args = ap.parse_args()

    keys = load_keys(args.file)
    if not keys:
        print("✗ Tidak ada API key (thk_live_... / status ok) di", args.file)
        return 1
    print(f"[+] Ditemukan {len(keys)} API key unik di {args.file}")

    # ── deteksi key yang sudah terhubung di 9router (PRIORITAS PERTAMA) ─────────────────────
    token = grok.generate_router_token()
    dup = {}
    connected = None
    if not args.no_db_check:
        connected = get_connected_keys(args.db)
        if connected is None:
            print("  ⚠ database 9router tidak terbaca -> deteksi duplikat dilewati "
                  "(gunakan --db <path>)")
        else:
            print(f"  [+] Terdeteksi {len(connected)} key sudah terhubung di 9router")
            new_keys = []
            for e, k in keys:
                if k in connected:
                    dup[(e, k)] = True
                else:
                    new_keys.append((e, k))
            if dup:
                print(f"  ✓ {len(dup)} key sudah terhubung (akan dilewati):")
                for (e, k) in list(dup.keys())[:3]:
                    print(f"      - {e}  {k[:20]}...")
                if len(dup) > 3:
                    print(f"      ... dan {len(dup)-3} lainnya")
            keys = new_keys
            print(f"  [+] Key baru yang belum terhubung: {len(keys)}")

    if not keys:
        print("\n[+] Semua key sudah terhubung ke 9router. Tidak ada yang perlu diimport.")
        return 0

    imported = set() if args.force else load_imported()
    pending = [(e, k) for e, k in keys if _md5(k) not in imported]
    print(f"[+] Belum di-import: {len(pending)} key "
          f"({len(keys) - len(pending)} sudah pernah di-import / --force)")

    # ── deteksi duplikat lanjutan (untuk fallback) ─────────────────────
    if args.no_db_check:
        print("  ⚠ deteksi duplikat via DB dinonaktifkan (--no-db-check)")
    else:
        if connected is not None:
            print("  ✓ Duplikat sudah difilter di tahap awal")

    print(f"[+] Siap dihubungkan: {len(pending)} key")

    providers = get_providers(args.router_base, token)
    target, default_model, max_pri = find_target_provider(providers, args.provider)
    if args.default_model:
        default_model = args.default_model
    start_pri = args.start_priority if args.start_priority is not None else (max_pri + 1)
    print(f"[+] Target provider: {target}")
    print(f"[+] defaultModel: {default_model} | start priority: {start_pri}")

    # Nama yang sudah terpakai di 9router (semua provider) -> hindari upsert.
    used_names = {str(c.get("name") or "").strip() for c in providers if c.get("name")}

    if args.dry_run:
        print("\n=== DRY-RUN (tidak ada perubahan) ===")
        _used = set(used_names)
        for i, (email, key) in enumerate(pending, 1):
            name = unique_name(f"{args.prefix} {i}", _used)
            _used.add(name)
            print(f"  POST priority={start_pri + i - 1} name={name!r} "
                  f"key={key[:16]}...  ({email})")
        print(f"\nAkan menambah {len(pending)} koneksi. Jalankan tanpa --dry-run untuk eksekusi.")
        return 0

    ok = fail = 0
    for i, (email, key) in enumerate(pending, 1):
        name = unique_name(f"{args.prefix} {i}", used_names)
        used_names.add(name)
        priority = start_pri + i - 1
        payload = {
            "provider": target,
            "apiKey": key,
            "name": name,
            "priority": priority,
            "defaultModel": default_model,
            "testStatus": "unknown",
        }
        try:
            resp = requests.post(
                f"{args.router_base}/api/providers",
                json=payload,
                cookies={"auth_token": token},
                headers={"Accept": "*/*", "Content-Type": "application/json"},
                timeout=20,
            )
        except Exception as e:
            print(f"  ✗ [{i}] POST gagal ({email}): {e}")
            fail += 1
            continue
        if resp.status_code in (200, 201):
            try:
                conn = resp.json().get("connection", {})
                cid = conn.get("id", "?")
            except Exception:
                cid = "?"
            mark_imported(key)
            ok += 1
            print(f"  ✓ [{i}] key {key[:16]}... -> connection {cid} (prio {priority})")
        else:
            try:
                err = resp.json().get("error") or resp.text[:150]
            except Exception:
                err = resp.text[:150]
            print(f"  ✗ [{i}] key {key[:16]}... ditolak: {err}")
            fail += 1

    print(f"\n=== Ringkasan ===")
    print(f"  Berhasil : {ok}")
    print(f"  Gagal    : {fail}")
    print(f"  Total    : {len(pending)}")
    if ok:
        print(f"  [+] {ok} key baru berhasil dihubungkan ke 9router.")
        print(f"  [-] Key yang sudah terhubung sebelumnya: {len(dup)}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
