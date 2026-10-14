#!/usr/bin/env python3
"""th_asn_expand.py — cari proxy RESIDENTIAL beneran utk th_harvest.

Sumber:
  A. Geonode public API (ada field isp/asn/city) -> filter ISP residential
     (mobile/broadband/home/fiber/cable...) + blokir ISP hosting/datacenter.
  B. /24 subnet expansion: dari prefix seed (IP geonode-residential + tier
     yang kelihatan ISP ID), scan IP acak x port umum -> yang hidup = kandidat
     residential segar (range ISP sama).

Output: append ke proxyfarm/residential_proxies.txt (dedupe).
  python3 th_asn_expand.py [--geo-pages 12] [--subnet 120] [--workers 150]
"""
import argparse
import concurrent.futures as cf
import json
import random
import re
import subprocess
import time
import urllib.request

SCRATCH = "/home/agentuser/.hermes/profiles/syadagentic/farm"
TIER = SCRATCH + "/proxyfarm/residential_proxies.txt"

RESI_KW = re.compile(
    r"mobile|broadband|home|fiber|fibre|cable|dsl|adsl|lte|gpon|"
    r"telkom|indosat|xl axiata|smartfren|firstmedia|biznet|myrepublic|"
    r"mnc|telkomsel|tri |3 |axis|net\.|net\b|inet|internet|"
    r"comcast|xfinity|verizon|at&t|att |spectrum|cox|centurylink|"
    r"orange|deutsche telekom|telefonica|vodafone|bt |virgin media|"
    r"rogers|bell |telstra|optus|singtel|ais |dtac|true |maxis|celcom|"
    r"digi |u mobile|pldt|globe |converge|sky |",
    re.I)
HOST_KW = re.compile(
    r"datacenter|data center|hosting|vps|cloud|server|digitalocean|"
    r"amazon|aws|google|microsoft|azure|ovh|vultr|hetzner|leaseweb|"
    r"datacamp|contabo|linode|scaleway|oracle|ibm|alibaba|tencent|"
    r"selectel|timeweb|hostkey|psychz|quadranet|worldstream|"
    r"internet provid|isp: |llc|ltd\.|limited$", re.I)


def geo_page(country, proto, page, limit=500):
    url = ("https://proxylist.geonode.com/api/proxy-list"
           "?country=%s&limit=%d&page=%d&sort_by=lastChecked"
           "&sort_type=desc&protocols=%s" % (country, limit, page, proto))
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
                          "Gecko/20100101 Firefox/128.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())["data"]
    except Exception as e:
        print("geo page err: %s" % str(e)[:80], flush=True)
        return []


def geo_residential():
    out = []
    # ID dulu (220.158 & 27.69 pernah trusted), lalu global
    for country in ("ID", "MY", "TH", "PH", "VN", "US", "BR", "IN", "all"):
        for proto in ("socks5", "socks4", "http"):
            for page in range(1, 9):
                rows = geo_page(country, proto, page)
                if not rows:
                    break
                n0 = len(out)
                for row in rows:
                    isp = (row.get("isp") or "") + " " + (row.get("org") or "")
                    if HOST_KW.search(isp):
                        continue
                    if not RESI_KW.search(isp):
                        continue
                    scheme = "socks5://" if "socks5" in row.get("protocols", []) \
                        else "socks4://" if "socks4" in row.get("protocols", []) \
                        else "http://"
                    out.append(scheme + row["ip"] + ":" + str(row["port"]))
                if len(out) > n0:
                    print("geo %s/%s p%d: +%d resi" % (country, proto, page,
                                                        len(out) - n0), flush=True)
    return out


def alive(px, timeout=9):
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", str(timeout), "-x", px, "https://api.ipify.org"],
            capture_output=True, timeout=timeout + 4)
        v = (r.stdout or b"").decode(errors="ignore").strip()
        return bool(v) and v.replace(".", "").isdigit()
    except Exception:
        return False


def subnet_scan(prefixes, per_subnet=18, workers=150):
    """Tiap /24: scan IP acak x port umum -> alive."""
    ports = (1080, 3128, 8080, 9050, 4145, 8888)
    cands = []
    for pre in prefixes:
        for _ in range(per_subnet):
            ip = "%s.%d" % (pre, random.randint(2, 254))
            cands.append("socks5://%s:%d" % (ip, random.choice(ports)))
    print("subnet: %d kandidat dari %d prefix" % (len(cands), len(prefixes)),
          flush=True)
    live = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(alive, px, 7): px for px in cands}
        done = 0
        for f in cf.as_completed(futs):
            done += 1
            if f.result():
                live.append(futs[f])
            if done % 1500 == 0:
                print("  subnet %d/%d, live %d" % (done, len(cands), len(live)),
                      flush=True)
    return live


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=150)
    ap.add_argument("--subnet", type=int, default=120,
                    help="jumlah /24 prefix utk scan")
    a = ap.parse_args()

    old = set()
    if os.path.exists(TIER):
        for l in open(TIER, errors="replace"):
            l = l.strip()
            if l and not l.startswith("#"):
                old.add(l.split("//")[-1].split(":")[0])

    t0 = time.time()
    cands = geo_residential()
    # dedupe by ip:port + buang yang udah ada (by ip)
    uniq, seen_ip = [], set()
    for px in cands:
        ip = px.split("//")[1].split(":")[0]
        if ip not in old and ip not in seen_ip:
            seen_ip.add(ip)
            uniq.append(px)
    print("geonode resi unik: %d -> health-check ..." % len(uniq), flush=True)

    live = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(alive, px): px for px in uniq}
        for f in cf.as_completed(futs):
            if f.result():
                live.append(futs[f])
    print("geonode LIVE: %d/%d (%.0fs)" % (len(live), len(uniq), time.time() - t0),
          flush=True)

    # /24 subnet expansion dari prefix yang live
    prefixes = sorted({".".join(p.split("//")[1].split(":")[0].split(".")[:3])
                       for p in live})[:a.subnet]
    sub_live = subnet_scan(prefixes, workers=a.workers) if prefixes else []
    print("subnet LIVE: %d" % len(sub_live), flush=True)

    total_new = live + sub_live
    if total_new:
        with open(TIER, "a") as f:
            for px in total_new:
                f.write(px + "\n")
    tier_n = sum(1 for l in open(TIER) if l.strip() and not l.startswith("#"))
    print("TOTAL baru: %d -> tier sekarang %d (%.0fs)" % (
        len(total_new), tier_n, time.time() - t0), flush=True)


if __name__ == "__main__":
    import os
    main()
