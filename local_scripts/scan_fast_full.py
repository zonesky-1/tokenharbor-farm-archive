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

print(f"Total US candidate: {len(us_candidates)}")

OUT_FILE = "/home/agentuser/.hermes/profiles/syadagentic/farm/exports/us_verified_alive.txt"

def check_alive(px):
    try:
        cmd = ["curl", "-s", "-m", "3", "--proxy", px, "http://api.ipify.org"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        out = r.stdout.strip()
        if out and out.replace(".", "").isdigit():
            with open(OUT_FILE, "a") as f:
                f.write(px + "\n")
            return True
    except:
        pass
    return False

# Scan batch 40.000 dengan 250 threads
batch = us_candidates[12000:52000]
print(f"Scanning next batch {len(batch)} with 250 threads...", flush=True)
t0 = time.time()
alive_cnt = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=250) as ex:
    for res in ex.map(check_alive, batch):
        if res:
            alive_cnt += 1

print(f"Batch selesai dalam {time.time()-t0:.1f}s! Ditemukan +{alive_cnt} IP US LIVE baru.", flush=True)
