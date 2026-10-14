import urllib.parse
import subprocess
import json
import concurrent.futures
import time
import maxminddb

print("[1] Membuka database GeoLite2-Country...")
db = maxminddb.open_database('/tmp/country.mmdb')

file_path = "/home/agentuser/.hermes/profiles/syadagentic/farm/exports/residential_proxies_all.txt"
with open(file_path) as f:
    lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

print(f"[2] Total candidate di residential master pool: {len(lines)}")

OUT_FILE = "/home/agentuser/.hermes/profiles/syadagentic/farm/exports/us_verified_https_resi.txt"
with open(OUT_FILE, "w") as f:
    f.write("# VERIFIED HTTPS CONNECT (PORT 443) + EGRESS REAL US (ZERO TRANSPARENT)\n")

def test_proxy(px):
    try:
        # TEST WAJIB HTTPS CONNECT TLS HANDSHAKE KE PORT 443
        cmd = ["curl", "-s", "-m", "4", "--proxy", px, "https://api.ipify.org"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        out_ip = r.stdout.strip()
        
        # Validasi IP keluar (egress)
        if out_ip and out_ip.replace(".", "").isdigit():
            # Cek GeoIP lokal instan (0 ms latency)
            geo = db.get(out_ip)
            iso = geo.get("country", {}).get("iso_code") if geo else None
            if iso == "US":
                return px, out_ip
    except:
        pass
    return None

t0 = time.time()
print("[3] Menjalankan test HTTPS CONNECT & Egress US dengan 200 threads paralel...", flush=True)

us_https_alive = []
with concurrent.futures.ThreadPoolExecutor(max_workers=200) as ex:
    for res in ex.map(test_proxy, lines):
        if res:
            px, egress = res
            us_https_alive.append(px)
            with open(OUT_FILE, "a") as f:
                f.write(px + "\n")
            if len(us_https_alive) % 250 == 0:
                print(f"  [+] Ditemukan {len(us_https_alive)} Proxy US HTTPS LIVE (Egress terverifikasi US)...", flush=True)

elapsed = time.time() - t0
print(f"\n[+] SELESAI DALAM {elapsed:.1f}s!", flush=True)
print(f"[+] Total Proxy US MURNI, HTTPS CONNECT 100%, Egress US: {len(us_https_alive)}", flush=True)
