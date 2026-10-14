#!/usr/bin/env python3
"""th_check20k.py — health-check massal daftar 20.000 proxy,
simpan yang LIVE (dedupe) ke residential_proxies.txt -> auto-kebaca
harvest (reload tier tiap 5 round).
"""
import urllib.request
import concurrent.futures as cf
import os, time, sys

SRC = "/home/agentuser/.hermes/profiles/syadagentic/cache/documents/doc_ec30cceafbb0_20.000_proxy.txt"
TIER = os.path.expanduser("~/.hermes/profiles/syadagentic/farm/proxyfarm/residential_proxies.txt")
CHECK = "http://www.gstatic.com/generate_204"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


def load():
    seen = set()
    out = []
    # jangan double sama tier lama
    if os.path.exists(TIER):
        for l in open(TIER, errors="replace"):
            l = l.strip()
            if l and not l.startswith("#") and "://" in l:
                seen.add(l.split("//")[-1])
    n_dup = 0
    for l in open(SRC, errors="replace"):
        l = l.strip()
        if not l or "://" not in l:
            continue
        k = l.split("//")[-1]
        if k in seen:
            n_dup += 1
            continue
        seen.add(k)
        out.append(l)
    return out, n_dup


def check(u):
    try:
        ph = urllib.request.ProxyHandler({"http": u, "https": u})
        op = urllib.request.build_opener(ph)
        op.addheaders = list(UA.items())
        r = op.open(CHECK, timeout=6)
        if r.status in (200, 204):
            return u
    except Exception:
        return None
    return None


def main():
    cands, dup = load()
    print(f"kandidat baru (setelah dedupe {dup} duplikat): {len(cands)}", flush=True)
    live = []
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=400) as ex:
        for i, r in enumerate(ex.map(check, cands, chunksize=25), 1):
            if r:
                live.append(r)
            if i % 2000 == 0:
                print(f"  {i}/{len(cands)} dicek, live={len(live)}, {time.time()-t0:.0f}s",
                      flush=True)
    # tulis ke tier (append dedupe)
    have = set()
    if os.path.exists(TIER):
        for l in open(TIER, errors="replace"):
            if "://" in l:
                have.add(l.split("//")[-1])
    baru = [x for x in live if x.split("//")[-1] not in have]
    if baru:
        with open(TIER, "a") as f:
            for x in baru:
                f.write(x + "\n")
    print(f"SELESAI: live {len(live)}/{len(cands)} -> +{len(baru)} masuk tier "
          f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
