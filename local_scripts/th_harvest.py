#!/usr/bin/env python3
"""th_harvest.py — scan residential tier utk cari IP trusted Turnstile,
lalu E2E signup TokenHarbor per IP (browser + solve = IP sama).

Target: N akun OK (email|password|apikey|ok) di tokenharbor_keys.txt.

CLI:
  python3 th_harvest.py --target 100 [--batch 8] [--max-rounds 60]

Flow per round:
  1. ambil `batch` proxy dari tier (acak, skip pernah-dicoba)
  2. paralel solve turnstile (camoufox, ~2.5 menit)
  3. tiap PASS -> jalankan tokenharbor.py --count 1 dgn TURNSTILE_PROXY=proxy
     (solve ulang di dlmnya juga pakai proxy sama; browser ikut proxy)
  4. status ok -> hitung; blocked/ratelimited -> buang proxy
Stop: target tercapai / tier habis / SIGTERM.
"""
import argparse
import json
import os
import urllib.request
import uuid
import random
import re
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.expanduser("~/.hermes/profiles/syadagentic/farm")
VENV = os.path.join(SCRATCH, "venv/bin/python")
SOLVER_DIR = os.path.join(SCRATCH, "turnstile-solver-x")
# SOLVER=px -> patchright (~15s/token), selain itu camoufox (~150s)
SOLVER = os.path.join(
    SOLVER_DIR,
    "solve_turnstile_px.py" if os.environ.get("SOLVER") == "px"
    else "solve_turnstile.py")
SOLVER_TIMEOUT = 60 if os.environ.get("SOLVER") == "px" else 180
TH_DIR = os.path.join(SCRATCH, "tokenharbour-farm/token-harbor-main")
TH = os.path.join(TH_DIR, "tokenharbor.py")
KEYS = os.path.join(TH_DIR, "tokenharbor_keys.txt")
TIER = os.path.join(SCRATCH, "proxyfarm/residential_proxies.txt")
SIG = {"stop": False}

NOTIFY_TOKEN_FILE = os.path.expanduser("~/.hermes/profiles/syadagentic/backups/config/farmbot_token.txt")
NOTIFY_CHAT = "7998819216"


def live_shot():
    """Grab layar Xvfb :99 -> live_screen.png (visual bukti farm jalan)."""
    p = os.path.join(SCRATCH, "proxyfarm/state/live_screen.png")
    try:
        subprocess.run([VENV, "-c",
                        "from PIL import ImageGrab; ImageGrab.grab(xdisplay=':99').save(r'%s')" % p],
                       capture_output=True, timeout=20)
    except Exception:
        pass
    return p


def notify(caption, photo=None):
    """Kirim notif visual (foto layar/hasil solve) ke Telegram operator."""
    try:
        tok = open(NOTIFY_TOKEN_FILE).read().strip()
        if photo and os.path.exists(photo) and os.path.getsize(photo) > 1000:
            b = uuid.uuid4().hex[:8].encode()
            body = (b"--" + b + b"\r\n"
                    b'Content-Disposition: form-data; name="chat_id"\r\n\r\n' + NOTIFY_CHAT.encode() + b"\r\n"
                    b"--" + b + b"\r\n"
                    b'Content-Disposition: form-data; name="caption"\r\n\r\n' + caption.encode() + b"\r\n"
                    b"--" + b + b"\r\n"
                    b'Content-Disposition: form-data; name="photo"; filename="live.png"\r\n'
                    b"Content-Type: image/png\r\n\r\n" + open(photo, "rb").read() + b"\r\n"
                    b"--" + b + b"--\r\n")
            req = urllib.request.Request(
                "https://api.telegram.org/bot%s/sendPhoto" % tok, data=body,
                headers={"Content-Type": "multipart/form-data; boundary=" + b.decode()})
        else:
            req = urllib.request.Request(
                "https://api.telegram.org/bot%s/sendMessage" % tok,
                data=json.dumps({"chat_id": NOTIFY_CHAT, "text": caption}).encode(),
                headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=25).read()
    except Exception:
        pass


def _sig(*a):
    SIG["stop"] = True


signal.signal(signal.SIGTERM, _sig)
signal.signal(signal.SIGINT, _sig)


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def ok_count():
    if not os.path.exists(KEYS):
        return 0
    n = 0
    for l in open(KEYS, errors="replace"):
        parts = l.strip().split("|")
        if len(parts) >= 4 and parts[3] in ("ok", "valid"):
            n += 1
    return n


def load_tier():
    sources = [
        TIER,
        os.path.join(SCRATCH, "proxyfarm", "stable_proxies.txt"),
        os.path.join(SCRATCH, "captcha-tools", "ws_farm_proxies.txt")
    ]
    out = []
    seen = set()
    for s in sources:
        if not os.path.exists(s):
            continue
        for l in open(s, errors="replace"):
            l = l.strip()
            if l and not l.startswith("#") and ("://" in l):
                k = l.split("//")[-1]
                if k not in seen:
                    seen.add(k)
                    out.append(l)
    return out


def solve_one(proxy, tag):
    """Return proxy kalau PASS, None kalau gagal. ~2.5 menit."""
    ip = re.sub(r"[^0-9.]", "", proxy.split("//")[1].split(":")[0])
    out = "/tmp/ths_%s.txt" % tag
    if os.path.exists(out):
        os.remove(out)
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":99")
    env["TURNSTILE_PROXY"] = proxy
    env["TURNSTILE_OUT"] = out
    try:
        pr = subprocess.run([VENV, SOLVER,
                        "https://tokenharbor.ai/login?mode=signup",
                        "0x4AAAAAADBuC8Knz1EJZx9-"],
                       env=env, capture_output=True, text=True,
                       timeout=SOLVER_TIMEOUT,
                       cwd=SOLVER_DIR)
        if not (os.path.exists(out) and os.path.getsize(out) > 100):
            with open(os.path.join(SCRATCH, "proxyfarm/state/ths_debug.log"), "a") as _dbg:
                _dbg.write("=== %s proxy=%s rc=%s ===\n%s\n" % (time.strftime("%H:%M:%S"), proxy, pr.returncode, (pr.stderr or "")[-800:]))
    except Exception as e:
        with open(os.path.join(SCRATCH, "proxyfarm/state/ths_debug.log"), "a") as _dbg:
            _dbg.write("=== %s proxy=%s EXC %s ===\n" % (time.strftime("%H:%M:%S"), proxy, e))
        return None
    if os.path.exists(out) and os.path.getsize(out) > 100:
        return proxy
    return None


def signup_one(proxy):
    """Jalankan 1 akun via tokenharbor.py dgn proxy. Return status string."""
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":99")
    env["TURNSTILE_PROXY"] = proxy
    # pakai token hasil solve_one tadi (skip re-solve -> hemat ~150s,
    # hindari proxy drop pas re-solve)
    ip = re.sub(r"[^0-9.]", "", proxy.split("//")[1].split(":")[0])
    tf = "/tmp/ths_%s.txt" % ip
    if os.path.exists(tf) and os.path.getsize(tf) > 100:
        env["TH_TOKEN_FILE"] = tf
    before = ok_count()
    try:
        r = subprocess.run([VENV, TH, "--count", "1", "--label", "harvest"],
                           env=env, capture_output=True, text=True, timeout=420,
                           cwd=TH_DIR)
        out = (r.stdout or "") + (r.stderr or "")
        # simpan debug signup (biar keliatan kenapa gagal)
        try:
            with open(os.path.join(SCRATCH, "th_signup_debug.log"), "a") as _df:
                _df.write("\n===== %s via %s =====\n%s\n" % (
                    time.strftime("%H:%M:%S"), proxy, out[-4000:]))
        except Exception:
            pass
    except subprocess.TimeoutExpired as te:
        try:
            part = te.stdout or te.stderr or b""
            if isinstance(part, bytes):
                part = part.decode(errors="replace")
            with open(os.path.join(SCRATCH, "th_signup_debug.log"), "a") as _df:
                _df.write("\n===== TIMEOUT %s via %s =====\n%s\n" % (
                    time.strftime("%H:%M:%S"), proxy, str(part)[-4000:]))
        except Exception:
            pass
        return "error:timeout"
    except Exception as e:
        return "error:%s" % e
    if ok_count() > before:
        return "ok"
    m = re.findall(r"SAVED: .*?\|(\w+)\s*$", out, re.M)
    if m:
        return m[-1]
    return "error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=100)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--max-rounds", type=int, default=60)
    a = ap.parse_args()

    tried = set()
    tier = load_tier()
    log("tier: %d proxy socks5 | target: %d akun ok | mulai" % (len(tier), a.target))
    notify("🚀 *TH farm mulai* — target %d akun | tier %d proxy" % (a.target, len(tier)))

    rnd = 0
    while ok_count() < a.target and rnd < a.max_rounds and not SIG["stop"]:
        rnd += 1
        if rnd == 1 or rnd % 5 == 0:
            tier = load_tier()  # reload — ekspansi bisa nambah tier sewaktu-waktu
        pool = [p for p in tier if p not in tried]
        if not pool:
            log("tier habis (%d dicoba) — berhenti" % len(tried))
            break
        # bias: 60% ambil dari 1.200 entry pertama (tier lama: resi/geonode yg
        # pernah ngasih trusted) — sisanya acak dari 19rb (mayoritas datacenter)
        head = pool[:1200]
        if len(head) >= a.batch and random.random() < 0.6:
            batch = random.sample(head, a.batch)
        else:
            batch = random.sample(pool, min(a.batch, len(pool)))
        tried.update(batch)
        log("round %d: solve %d proxy (ok sekarang %d/%d)" % (
            rnd, len(batch), ok_count(), a.target))

        trusted = []
        with ThreadPoolExecutor(max_workers=len(batch)) as ex:
            futs = {ex.submit(solve_one, p, str(i)): p
                    for i, p in enumerate(batch)}
            for f in as_completed(futs):
                p = futs[f]
                try:
                    r = f.result()
                except Exception:
                    r = None
                if r:
                    trusted.append(r)
                    log("  TRUSTED: %s" % r)
                    notify("✅ *TRUSTED* %s — signup jalan…" % r.split("//")[1])
        log("  trusted round ini: %d/%d" % (len(trusted), len(batch)))

        for px in trusted:
            if SIG["stop"] or ok_count() >= a.target:
                break
            st = signup_one(px)
            log("  signup via %s -> %s (ok total %d)" % (
                px.split("//")[1], st, ok_count()))
            notify("📝 signup %s → *%s* (ok total %d)" % (px.split("//")[1], st, ok_count()))
            if st != "ok":
                tried.add(px)  # IP burn
        log("  progres: %d/%d ok" % (ok_count(), a.target))

    log("SELESAI harvest: %d/%d akun ok (proxy dicoba %d)" % (
        ok_count(), a.target, len(tried)))


if __name__ == "__main__":
    main()
