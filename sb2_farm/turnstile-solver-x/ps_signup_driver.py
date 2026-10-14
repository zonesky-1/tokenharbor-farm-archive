#!/usr/bin/env python3
"""ProxyScrape signup driver (pola Webshare): cek proxy -> mint turnstile -> POST register.
Password TIDAK dicetak. Hasil ke stdout + ps_creds.json."""
import subprocess, secrets, json, time, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.expanduser("~/.hermes/profiles/syadagentic/farm/venv/bin/python")
RESI = os.path.expanduser("~/.hermes/profiles/syadagentic/farm/proxyfarm/residential_proxies.txt")
URL = "https://dashboard.proxyscrape.com/v2/sign-up"
SITEKEY = "0x4AAAAAAAFWUVCKyusT9T8r"
ENDPOINT = "https://dashboard.proxyscrape.com/v2/v4/account/auth/register"
TOKEN_FILE = "/tmp/turnstile_token.txt"


def proxies():
    out = []
    for l in open(RESI):
        l = l.strip()
        if l and not l.startswith("#") and l.startswith(("socks5://", "http://")):
            out.append(l)
    return out


def alive(px):
    try:
        r = subprocess.run(["curl", "-s", "-m", "7", "-x", px, "https://api.ipify.org"],
                           capture_output=True, text=True, timeout=10)
        v = r.stdout.strip()
        return bool(v) and v.replace(".", "").isdigit()
    except Exception:
        return False


def mint(px):
    if os.path.exists(TOKEN_FILE):
        os.unlink(TOKEN_FILE)
    env = dict(os.environ, TURNSTILE_PROXY=px)
    try:
        r = subprocess.run(
            [VENV, os.path.join(BASE, "solve_turnstile.py"), URL, SITEKEY],
            capture_output=True, text=True, timeout=150, cwd=BASE, env=env)
        log = (r.stdout + r.stderr)
        ok = "RESULT=PASS" in log
        tok = open(TOKEN_FILE).read().strip() if os.path.exists(TOKEN_FILE) else ""
        return ok and tok, log.strip().splitlines()[-3:]
    except Exception as e:
        return False, [str(e)]


def register(email, pw, tok):
    r = subprocess.run(
        ["curl", "-s", "-m", "25", "-X", "POST", ENDPOINT,
         "-F", "email=" + email, "-F", "password=" + pw,
         "-F", "cf_turnstile_token=" + tok,
         "-H", "Origin: https://dashboard.proxyscrape.com",
         "-H", "Referer: https://dashboard.proxyscrape.com/v2/sign-up"],
        capture_output=True, text=True, timeout=40)
    return r.stdout.strip()


def main():
    cands = proxies()
    random_order = secrets.SystemRandom().shuffle(cands) if False else None
    secrets.SystemRandom().shuffle(cands)
    tried = 0
    for px in cands[:25]:
        if not alive(px):
            continue
        tried += 1
        print(f"[proxy] hidup, mint via {px}", flush=True)
        ok, log = mint(px)
        if not ok:
            print(f"[mint] gagal: {log}", flush=True)
            continue
        print("[mint] PASS, POST register (token age <60s)", flush=True)
        email = "ps" + secrets.token_hex(5) + "@maxxspace.com"
        pw = "Ps!" + secrets.token_urlsafe(14)
        resp = register(email, pw, open(TOKEN_FILE).read().strip())
        print("RESP:", resp[:700], flush=True)
        try:
            data = json.loads(resp)
        except Exception:
            data = {}
        if data.get("success") is True or data.get("access_token"):
            json.dump({"email": email, "password": pw, "resp": resp, "ts": time.time()},
                      open(os.path.join(BASE, "ps_creds.json"), "w"), indent=1)
            print("RESULT=OK  (creds -> ps_creds.json)  email=" + email, flush=True)
            return
        # token bisa dipakai ulang? kalau cuma token bermasalah, lanjut loop dgn proxy baru
        if "token" in str(data.get("message", "")).lower():
            print("[post] token ditolak, lanjut proxy baru...", flush=True)
            continue
        # selain token = kemungkinan email block -> tetap catat pesannya
        print("[post] non-token error, catat & tetap lanjut:", data.get("message"), flush=True)
    print(f"RESULT=FAIL (proxy hidup dicoba: {tried})", flush=True)


if __name__ == "__main__":
    main()
