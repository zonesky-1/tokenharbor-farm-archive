#!/usr/bin/env python3
"""Refill th_clean_verified.txt: test CONNECT tokenharbor utk kandidat fresh."""
import subprocess, concurrent.futures, time
RESI = "/home/ubuntu/farm/proxyfarm/residential_proxies.txt"
OUT  = "/home/ubuntu/farm/proxyfarm/th_clean_verified.txt"
BURN = "/home/ubuntu/farm/proxyfarm/burnt.txt"
def main():
    burnt = set()
    try: burnt = set(l.strip() for l in open(BURN) if l.strip())
    except: pass
    have = set(l.strip() for l in open(OUT) if l.strip())
    lines = [l.strip() for l in open(RESI) if l.strip() and not l.startswith("#")]
    cands = [l for l in lines if l.split("@")[-1] not in burnt and l not in have]
    if len(have) > 1200 or not cands:
        print(f"pool={len(have)} cukup, skip")
        return
    need = 800
    import random
    sample = random.sample(cands, min(need, len(cands)))
    def test(px):
        try:
            r = subprocess.run(["curl","-s","-m","6","--proxy",px,"https://tokenharbor.ai/login?mode=signup","-o","/dev/null","-w","%{http_code}"], capture_output=True, text=True, timeout=8)
            return px if r.stdout.strip()=="200" else None
        except: return None
    t0=time.time(); clean=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as ex:
        for res in ex.map(test, sample):
            if res: clean.append(res)
    with open(OUT,"a") as f:
        for c in clean: f.write(c+"\n")
    print(f"+{len(clean)} clean in {time.time()-t0:.0f}s (pool -> {len(have)+len(clean)})")
if __name__ == "__main__":
    main()
