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

OUT_US_SG = "/home/agentuser/.hermes/profiles/syadagentic/farm/exports/https_verified_us_sg.txt"
OUT_ALL_HTTPS = "/home/agentuser/.hermes/profiles/syadagentic/farm/exports/https_verified_all_global.txt"

with open(OUT_US_SG, "w") as f:
    f.write("# 100% VERIFIED HTTPS CONNECT (PORT 443) - US & SG ONLY\n")

with open(OUT_ALL_HTTPS, "w") as f:
    f.write("# 100% VERIFIED HTTPS CONNECT (PORT 443) - ALL WORKING RESIDENTIAL\n")

def test_proxy(px):
    try:
        # TEST WAJIB HTTPS CONNECT TLS HANDSHAKE KE PORT 443
        cmd = ["curl", "-s", "-m", "4", "--proxy", px, "https://api.ipify.org"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        out_ip = r.stdout.strip()
        
        if out_ip and out_ip.replace(".", "").isdigit():
            geo = db.get(out_ip)
            iso = geo.get("country", {}).get("iso_code") if geo else "UNK"
            return px, out_ip, iso
    except:
        pass
    return None

t0 = time.time()
print("[3] Menjalankan test HTTPS CONNECT & Klasifikasi Negara dengan 250 threads paralel...", flush=True)

cnt_us_sg = 0
cnt_all = 0
countries_stat = {}

with concurrent.futures.ThreadPoolExecutor(max_workers=250) as ex:
    for res in ex.map(test_proxy, lines):
        if res:
            px, egress, iso = res
            cnt_all += 1
            countries_stat[iso] = countries_stat.get(iso, 0) + 1
            
            with open(OUT_ALL_HTTPS, "a") as f_all:
                f_all.write(px + "\n")
                
            if iso in ("US", "SG"):
                cnt_us_sg += 1
                with open(OUT_US_SG, "a") as f_us_sg:
                    f_us_sg.write(px + "\n")
                    
            if cnt_all % 500 == 0:
                print(f"  [+] Terverifikasi HTTPS CONNECT: {cnt_all}/{len(lines)} (US/SG: {cnt_us_sg})...", flush=True)

elapsed = time.time() - t0
print(f"\n[+] SELESAI DALAM {elapsed:.1f}s!", flush=True)
print(f"[+] Total Berhasil HTTPS CONNECT: {cnt_all}")
print(f"[+] Khusus US + SG: {cnt_us_sg}")
print(f"[+] Breakdown Negara Egress: {countries_stat}", flush=True)
