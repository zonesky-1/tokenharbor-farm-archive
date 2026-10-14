#!/usr/bin/env python3
import os
import sys
import time
import json
import uuid
import datetime
import subprocess
import concurrent.futures
import random

SB2_HOST = "ubuntu@100.81.10.96"
SB2_KEY = "/home/agentuser/.ssh/agentuser_vps"
VIDEO_HOST = "agentuser@100.67.195.35"
VIDEO_KEY = "/home/agentuser/.ssh/id_ed25519"
ROUTER_HOST = "agentuser@100.79.55.60"
ROUTER_KEY = "/home/agentuser/.ssh/id_ed25519"

NODE_ID = "openai-compatible-chat-f170848c-b8b0-4f8c-9e26-19bf84e210a9"
TEST_URL = "https://tokenharbor.ai/v1/chat/completions"

CACHE_DIR = "/home/agentuser/.hermes/profiles/syadagentic/farm/sync_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = f"{CACHE_DIR}/9r_registered_keys.json"
PROXY_FILE = "/home/agentuser/.hermes/profiles/syadagentic/farm/exports/us_verified_https_resi.txt"

def run_ssh(host, key, cmd, timeout=60):
    full_cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
        "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=3",
        "-i", key, host, cmd
    ]
    r = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.stderr, r.returncode

def load_proxies():
    try:
        with open(PROXY_FILE) as f:
            return [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except:
        return []

def pull_farm_keys():
    records = []
    seen = set()

    # Tarik dari SB2
    try:
        out, _, code = run_ssh(SB2_HOST, SB2_KEY, "cat /home/ubuntu/farm/tokenharbor/tokenharbor_keys.txt 2>/dev/null")
        if code == 0:
            for line in out.splitlines():
                if "|ok" in line:
                    parts = line.strip().split("|")
                    if len(parts) >= 3:
                        email, pw, k = parts[0].strip(), parts[1].strip(), parts[2].strip()
                        if k.startswith("thk_live_") and k not in seen:
                            seen.add(k)
                            records.append((email, pw, k))
    except Exception as e:
        print(f"[PULL] Err SB2: {e}")

    # Tarik dari VM Video
    try:
        out, _, code = run_ssh(VIDEO_HOST, VIDEO_KEY, "cat /home/agentuser/farm/tokenharbor/tokenharbor_keys.txt 2>/dev/null")
        if code == 0:
            for line in out.splitlines():
                if "|ok" in line:
                    parts = line.strip().split("|")
                    if len(parts) >= 3:
                        email, pw, k = parts[0].strip(), parts[1].strip(), parts[2].strip()
                        if k.startswith("thk_live_") and k not in seen:
                            seen.add(k)
                            records.append((email, pw, k))
    except Exception as e:
        print(f"[PULL] Err Video: {e}")

    return records

def get_router_keys():
    # Coba baca dari remote 9Router
    cmd = f"""python3 -c "
import sqlite3, json
con = sqlite3.connect('/var/lib/9router/db/data.sqlite')
cur = con.cursor()
cur.execute('SELECT data FROM providerConnections WHERE provider=\\"{NODE_ID}\\"')
keys = [json.loads(r[0])['apiKey'] for r in cur.fetchall() if 'apiKey' in json.loads(r[0])]
print(json.dumps(keys))
" """
    out, _, code = run_ssh(ROUTER_HOST, ROUTER_KEY, cmd, timeout=30)
    if code == 0 and out.strip():
        try:
            keys = set(json.loads(out.strip()))
            with open(CACHE_FILE, "w") as f:
                json.dump(list(keys), f)
            return keys
        except:
            pass

    # Fallback ke cache lokal
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return set(json.load(f))
        except:
            pass
    return set()

def verify_single_key(item, proxies):
    rec, px = item
    email, pw, key = rec
    payload = json.dumps({
        "model": "deepseek-v4-flash:free",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1
    })
    
    cmd = [
        "curl", "-s", "-m", "7",
        "--proxy", px,
        "-H", f"Authorization: Bearer {key}",
        "-H", "Content-Type: application/json",
        TEST_URL, "-d", payload
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        resp = r.stdout
        if '"id":"chatcmpl-' in resp or '"object":"chat.completion"' in resp:
            return rec, True, "OK"
        if "free_tier_limit_reached" in resp or "allowance" in resp:
            return rec, False, "QUOTA_EXHAUSTED"
        if "Invalid or revoked" in resp:
            return rec, False, "REVOKED"
        if "Rate limit reached" in resp or "Network rate limit" in resp:
            # IP proxy kena rate limit, coba sekali direct/proxy lain
            return rec, False, "RATE_LIMITED_IP"
        return rec, False, f"ERR:{resp[:60]}"
    except Exception as e:
        return rec, False, f"TIMEOUT"

def inject_to_9router(valid_records):
    if not valid_records:
        return 0

    json_payload_path = f"{CACHE_DIR}/to_inject.json"
    with open(json_payload_path, "w") as f:
        json.dump(valid_records, f)

    scp_cmd = [
        "scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        "-i", ROUTER_KEY, json_payload_path, f"{ROUTER_HOST}:/tmp/to_inject.json"
    ]
    r = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        print(f"[INJECT] SCP fail: {r.stderr}")
        return 0

    remote_script = f"""
python3 - << 'PYEOF'
import sqlite3, json, uuid, datetime

DB_PATH = "/var/lib/9router/db/data.sqlite"
NODE_ID = "{NODE_ID}"

with open("/tmp/to_inject.json") as f:
    records = json.load(f)

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

cur.execute("SELECT data FROM providerConnections WHERE provider=?", (NODE_ID,))
existing = set()
for (d_str,) in cur.fetchall():
    try:
        d = json.loads(d_str)
        if "apiKey" in d: existing.add(d["apiKey"])
    except: pass

now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
inserted = 0
for email, pw, key in records:
    if key in existing:
        continue
    conn_id = str(uuid.uuid4())
    username = email.split("@")[0]
    conn_name = f"TH-{{username}}"
    conn_data = {{
        "defaultModel": "H",
        "apiKey": key,
        "testStatus": "active",
        "providerSpecificData": {{
            "prefix": "Th",
            "apiType": "chat",
            "baseUrl": "https://tokenharbor.ai/v1",
            "nodeName": "Token harbor",
            "connectionProxyEnabled": False,
            "connectionProxyUrl": "",
            "connectionNoProxy": ""
        }}
    }}
    cur.execute('''
        INSERT INTO providerConnections (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (conn_id, NODE_ID, "apikey", conn_name, email, 1, 1, json.dumps(conn_data), now_iso, now_iso))
    existing.add(key)
    inserted += 1

con.commit()
print(f"INSERTED:{{inserted}}")
con.close()
PYEOF
sudo -n systemctl restart 9router
"""
    out, _, code = run_ssh(ROUTER_HOST, ROUTER_KEY, remote_script, timeout=45)
    for line in out.splitlines():
        if line.startswith("INSERTED:"):
            # Update cache lokal
            new_keys = [rec[2] for rec in valid_records]
            try:
                with open(CACHE_FILE) as f:
                    cached = set(json.load(f))
                cached.update(new_keys)
                with open(CACHE_FILE, "w") as f:
                    json.dump(list(cached), f)
            except:
                pass
            return int(line.split(":")[1])
    return 0

def run_sync_cycle():
    t0 = time.time()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{now_str}] === MEMULAI SINKRONISASI OTOMATIS TOKEN HARBOR -> 9ROUTER ===", flush=True)
    
    farm_keys = pull_farm_keys()
    print(f"-> Total key '|ok' terkumpul dari cluster farm: {len(farm_keys)} akun", flush=True)

    router_keys = get_router_keys()
    print(f"-> Key yang sudah aktif di 9Router: {len(router_keys)} akun", flush=True)

    unregistered = [r for r in farm_keys if r[2] not in router_keys]
    print(f"-> Key fresh baru yang belum masuk 9Router: {len(unregistered)} akun", flush=True)

    if not unregistered:
        print("-> [OK] 9Router sudah 100% sinkron dengan seluruh akun farm yang ada. Standby.", flush=True)
        return

    proxies = load_proxies()
    if not proxies:
        print("-> [WARN] Tidak ada list proxy, verifikasi direct...")
        proxies = [""]

    print(f"-> Menjalankan verifikasi USAGE QUOTA AKTIF (Residential Proxy Isolated, 20 workers)...", flush=True)
    
    # Pasangkan setiap key dengan proxy residential yang berbeda agar bebas ip rate-limit
    tasks = []
    for idx, rec in enumerate(unregistered):
        px = proxies[idx % len(proxies)]
        tasks.append((rec, px))

    valid_with_quota = []
    retry_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        for rec, ok, status in ex.map(lambda item: verify_single_key(item, proxies), tasks):
            if ok:
                valid_with_quota.append(rec)
            elif status == "RATE_LIMITED_IP":
                retry_list.append(rec)
            else:
                print(f"   [DISCARD] {rec[0]}: {status}", flush=True)

    # Retry yang kena IP rate limit dengan proxy lain
    if retry_list:
        print(f"-> Retrying {len(retry_list)} keys dengan proxy cadangan...", flush=True)
        random.shuffle(proxies)
        retry_tasks = [(rec, proxies[i % len(proxies)]) for i, rec in enumerate(retry_list)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            for rec, ok, status in ex.map(lambda item: verify_single_key(item, proxies), retry_tasks):
                if ok:
                    valid_with_quota.append(rec)
                else:
                    print(f"   [DISCARD RETRY] {rec[0]}: {status}", flush=True)

    print(f"-> Hasil verifikasi: {len(valid_with_quota)} / {len(unregistered)} key LOLOS (MEMILIKI KUOTA AKTIF)!", flush=True)

    if valid_with_quota:
        inserted = inject_to_9router(valid_with_quota)
        print(f"-> 🔥 SUKSES INJEKSI +{inserted} CONNECTION BARU KE 9ROUTER & RESTART SERVICE!", flush=True)
    else:
        print("-> Tidak ada key baru yang diinjeksi pada siklus ini.", flush=True)

    print(f"-> Siklus sinkronisasi selesai dalam {time.time()-t0:.1f}s.", flush=True)

def main():
    if "--loop" in sys.argv:
        print("=== DAEMON AUTO-SINKRON 9ROUTER AKTIF (Cek tiap 120 detik) ===", flush=True)
        while True:
            try:
                run_sync_cycle()
            except Exception as e:
                print(f"[DAEMON ERR] {e}", flush=True)
            time.sleep(120)
    else:
        run_sync_cycle()

if __name__ == "__main__":
    main()
