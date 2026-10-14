import maxminddb
import re
import subprocess
import concurrent.futures
import time

db = maxminddb.open_database('/tmp/country.mmdb')
IP_RE = re.compile(r'^(?:https?|socks[45])://(\d{1,3}(?:\.\d{1,3}){3}):\d+$')

us_candidates = []
with open("/tmp/fresh_unseen.txt") as f:
    for line in f:
        line = line.strip()
        m = IP_RE.match(line)
        if m:
            ip = m.group(1)
            try:
                res = db.get(ip)
                if res and res.get("country", {}).get("iso_code") == "US":
                    us_candidates.append(line)
            except:
                pass

print(f"Total US candidate: {len(us_candidates)}", flush=True)

OUT_FILE = "/home/agentuser/.hermes/profiles/syadagentic/farm/exports/us_verified_alive.txt"

# Ambil IP yang sudah tercatat agar tidak ada duplikasi
already = set()
try:
    with open(OUT_FILE) as f:
        for l in f:
            already.add(l.strip())
except:
    pass

def check_alive(px):
    if px in already:
        return False
    try:
        cmd = ["curl", "-s", "-m", "3", "--proxy", px, "http://api.ipify.org"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        out = r.stdout.strip()
        if out and out.replace(".", "").isdigit():
            with open(OUT_FILE, "a") as f:
                f.write(px + "\n")
            already.add(px)
            return True
    except:
        pass
    return False

# Scan seluruh sisa kandidat dari indeks 52.000 sampai habis (~84.000 IP) dengan 300 threads
batch = us_candidates[52000:]
print(f"Scanning sisa batch {len(batch)} dengan 300 threads...", flush=True)
t0 = time.time()
alive_cnt = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=300) as ex:
    for res in ex.map(check_alive, batch):
        if res:
            alive_cnt += 1

print(f"Full scan selesai dalam {time.time()-t0:.1f}s! Ditemukan +{alive_cnt} IP US LIVE baru.", flush=True)
