#!/usr/bin/env python3
"""
solve_turnstile.py — Native Turnstile Solver via Camoufox & Xvfb :99
Optimized for TokenHarbor lazy-rendered Turnstile widget.
"""
import os, sys, time, json, random, string
import urllib.parse as up

def solve(page):
    t0 = time.time()
    clicked = False
    submitted = False
    token = ""
    deadline = t0 + 60

    print("[*] Starting fast Turnstile solve...", flush=True)

    # 1. Trigger lazy widget immediately by filling form and clicking submit
    try:
        user = "th" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        pw = "Pass_" + "".join(random.choices(string.ascii_letters + string.digits, k=10)) + "!99"
        page.fill("input[name=email], input[type=email]", f"{user}@maxxspace.com")
        page.fill("input[name=password], input[type=password]", pw)
        page.click("button[type=submit], button:has-text('Create account')")
        submitted = True
        print("[*] Form submitted to trigger Turnstile", flush=True)
    except Exception as e:
        print(f"[!] Form submit trigger: {e}", flush=True)

    # 2. Wait for iframe and click checkbox
    while time.time() < deadline:
        token = page.evaluate("""() => {
            const f = document.querySelector('input[name="cf-turnstile-response"], textarea[name="cf-turnstile-response"]');
            return (f && f.value && f.value.length > 50) ? f.value : (window.__ts_tok || '');
        }""")
        if token and len(token) > 50:
            print(f"🎉 GOT TOKEN! Length: {len(token)} in {time.time()-t0:.1f}s", flush=True)
            break

        el = time.time() - t0
        if not clicked and el >= 1.5:
            # Check for Cloudflare iframe
            for f in page.frames:
                if "challenges.cloudflare.com" in f.url:
                    try:
                        f.click("input[type='checkbox'], #challenge-stage, .ctp-checkbox-label, body", timeout=1500)
                        clicked = True
                        print(f"[*] Clicked checkbox inside iframe {f.name} ({el:.1f}s)", flush=True)
                        break
                    except Exception:
                        pass
            if not clicked:
                try:
                    box = page.locator("iframe[src*='challenges.cloudflare.com']").first.bounding_box()
                    if box and box.get("width"):
                        page.mouse.click(box["x"] + 28, box["y"] + box["height"] / 2)
                        clicked = True
                        print(f"[*] Clicked checkbox bounding box ({el:.1f}s)", flush=True)
                except Exception:
                    pass

        time.sleep(0.5)

    if token:
        out = os.environ.get("TURNSTILE_OUT", "/tmp/turnstile_token.txt")
        with open(out, "w") as f:
            f.write(token)
        print(f"SAVED={out}", flush=True)
        return token
    return ""

def main():
    if len(sys.argv) < 2:
        print("Usage: solve_turnstile.py <url> [sitekey]")
        sys.exit(1)
    url = sys.argv[1]

    from camoufox.sync_api import Camoufox
    os.environ["DISPLAY"] = ":99"

    proxy = os.environ.get("TURNSTILE_PROXY") or os.environ.get("BROWSER_PROXY")
    kw = {"headless": True, "humanize": True, "geoip": False}
    if proxy:
        pu = up.urlparse(proxy)
        if pu.username:
            kw["proxy"] = {"server": f"{pu.scheme}://{pu.hostname}:{pu.port}",
                           "username": pu.username, "password": pu.password or ""}
        else:
            kw["proxy"] = {"server": proxy}

    # geoip=True butuh cek IP via ipecho.net — beberapa proxy nge-400.
    # Coba dengan proxy URL lengkap; kalau gagal -> geoip=False (tetap solve).
    if proxy:
        try:
            import camoufox.ip as _ip
            _ip.public_ip(proxy)  # full URL (server+user+pass)
            kw["geoip"] = True
            print("[solve] geoip=True (IP check OK)", flush=True)
        except Exception as e:
            kw["geoip"] = False
            print(f"[solve] geoip fallback False ({str(e)[:60]})", flush=True)

    with Camoufox(**kw) as b:
        page = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
        for attempt in range(3):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                break
            except Exception as e:
                print(f"[!] Goto retry {attempt+1}: {e}", flush=True)
                time.sleep(1)

        token = solve(page)
        if token:
            print("RESULT=PASS")
            sys.exit(0)
        else:
            print("RESULT=FAIL")
            sys.exit(1)

if __name__ == "__main__":
    main()
