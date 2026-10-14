#!/usr/bin/env python3
"""th_expand_tier.py — perbesar residential tier utk th_harvest.

Sumber gratis: proxifly (gh raw), proxyscrape v2 API, monosans (gh),
free-proxy-list gh. Health-check paralel (curl -> ipify). Yang hidup
di-append ke proxyfarm/residential_proxies.txt (dedupe).

  python3 th_expand_tier.py [--pull 3] [--workers 120]

Catatan: filter "residential" final = turnstile solver sendiri (yang
trusted dipakai th_harvest); sini cuma perlu banyak kandidat hidup.
"""
import argparse
import concurrent.futures as cf
import os
import subprocess
import time
import urllib.request

SCRATCH = os.path.expanduser("~/.hermes/profiles/syadagentic/farm")
TIER = os.path.join(SCRATCH, "proxyfarm/residential_proxies.txt")

SOURCES = [
    # (nama, cara ambil)
    ("proxifly-socks5",
     "curl -s -m 30 https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt"),
    ("proxifly-socks4",
     "curl -s -m 30 https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt"),
    ("proxifly-http",
     "curl -s -m 30 https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt"),
    ("monosans",
     "curl -s -m 30 https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt"),
    ("monosans-http",
     "curl -s -m 30 https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
    ("ps-socks5",
     "curl -s -m 30 'https://api.proxyscrape.com/v2/?request=getproxies&proxy=socks5&timeout=10000&country=all'"),
    ("ps-socks4",
     "curl -s -m 30 'https://api.proxyscrape.com/v2/?request=getproxies&proxy=socks4&timeout=10000&country=all'"),
    ("ps-http",
     "curl -s -m 30 'https://api.proxyscrape.com/v2/?request=getproxies&proxy=http&timeout=10000&country=all'"),
]

SCHEME = {"socks5": "socks5://", "socks4": "socks4://", "http": "http://"}


def norm(name, line):
    line = line.strip()
    if not line or ":" not in line:
        return None
    # data.txt proxifly: "ip:port" atau "socks5://ip:port"
    if "://" in line:
        return line if line.startswith(("socks", "http")) else None
    if "socks5" in name:
        return "socks5://" + line
    if "socks4" in name:
        return "socks4://" + line
    return "http://" + line


def alive(px, timeout=9):
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", str(timeout), "-x", px, "https://api.ipify.org"],
            capture_output=True, timeout=timeout + 4)
        v = (r.stdout or b"").decode(errors="ignore").strip()
        return bool(v) and v.replace(".", "").isdigit()
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=120)
    a = ap.parse_args()

    old = set()
    if os.path.exists(TIER):
        for l in open(TIER, errors="replace"):
            l = l.strip()
            if l and not l.startswith("#"):
                old.add(l.split("//")[-1])  # dedupe by host:port

    cands = []
    for name, cmd in SOURCES:
        url = cmd.split("curl -s -m 30 ")[-1].strip("'")
        try:
            with urllib.request.urlopen(url, timeout=40) as resp:
                text = resp.read().decode(errors="ignore")
        except Exception as e:
            print("%s: ERR %s" % (name, e), flush=True)
            continue
        lines = text.splitlines()
        n = 0
        for l in lines:
            px = norm(name, l)
            if px and px.split("//")[-1] not in old:
                cands.append(px)
                n += 1
        print("%s: %d kandidat baru" % (name, n), flush=True)

    # dedupe in-cand
    seen = set()
    uniq = []
    for px in cands:
        k = px.split("//")[-1]
        if k not in seen:
            seen.add(k)
            uniq.append(px)
    print("total kandidat unik: %d -> health-check (%d worker) ..."
          % (len(uniq), a.workers), flush=True)

    t0 = time.time()
    live = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(alive, px): px for px in uniq}
        done = 0
        for f in cf.as_completed(futs):
            done += 1
            if f.result():
                live.append(futs[f])
            if done % 500 == 0:
                print("  ... %d/%d dicek, %d live (%.0fs)" % (
                    done, len(uniq), len(live), time.time() - t0), flush=True)

    if live:
        with open(TIER, "a") as f:
            for px in live:
                f.write(px + "\n")
    total = sum(1 for l in open(TIER) if l.strip() and not l.startswith("#"))
    print("LIVE %d/%d -> tier sekarang %d baris (%.0fs)" % (
        len(live), len(uniq), total, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
