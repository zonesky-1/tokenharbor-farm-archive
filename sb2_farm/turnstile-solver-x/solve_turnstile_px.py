#!/usr/bin/env python3
"""solve_turnstile_px.py — patchright Turnstile solver (pengganti camoufox).

Interface IDENTIK solve_turnstile.py (drop-in buat th_harvest):
  argv: <url> <sitekey>
  env:  TURNSTILE_PROXY (socks5:// atau http://host:port, opsional)
        TURNSTILE_OUT   (default /tmp/turnstile_token.txt)
  stdout: RESULT=PASS token=Nchar  /  RESULT=FAIL <alasan>

Kenapa patchright: chrome patched anti-CDP-detect; ~13s per token
(skill evidence 2026-10-09) vs camoufox ~150s. Lebih ringan (no Xvfb
kalau headless). Keluaran = token dari DOM cf-turnstile-response.
"""
import os
import sys
import time


def main():
    if len(sys.argv) < 3:
        print("usage: solve_turnstile_px.py <url> <sitekey>", flush=True)
        sys.exit(2)
    page_url, sitekey = sys.argv[1], sys.argv[2]
    out_path = os.environ.get("TURNSTILE_OUT", "/tmp/turnstile_token.txt")
    proxy = os.environ.get("TURNSTILE_PROXY")
    wait = int(os.environ.get("TURNSTILE_WAIT", "30"))

    from patchright.sync_api import sync_playwright

    kw = {"headless": True,
          "args": ["--no-sandbox", "--disable-dev-shm-usage",
                   "--disable-blink-features=AutomationControlled"]}
    if proxy:
        kw["proxy"] = {"server": proxy}

    t0 = time.time()
    tok = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(**kw)
        ctx = browser.new_context(viewport={"width": 1300, "height": 900},
                                  locale="en-US")
        page = ctx.new_page()
        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print("RESULT=FAIL (goto: %s)" % str(e)[:120], flush=True)
            browser.close()
            sys.exit(1)

        # iframe widget turnstile (filter sitekey kalau ada di src)
        try:
            page.wait_for_selector("iframe[src*='challenges.cloudflare.com']",
                                   state="attached", timeout=15000)
        except Exception:
            pass
        time.sleep(1.5)

        frames = page.locator("iframe[src*='challenges.cloudflare.com']")
        n = frames.count()
        target = 0
        if n > 1:
            for i in range(n):
                try:
                    src = frames.nth(i).get_attribute("src") or ""
                except Exception:
                    src = ""
                if sitekey and sitekey in src:
                    target = i
                    break

        # klik widget human-ish (mouse move + click)
        clicked = False
        try:
            b = frames.nth(target).bounding_box()
            if b:
                page.mouse.move(b["x"] + b["width"] * 0.12,
                                b["y"] + b["height"] / 2, steps=12)
                time.sleep(0.5)
                page.mouse.click(b["x"] + b["width"] * 0.08,
                                 b["y"] + b["height"] / 2)
                clicked = True
        except Exception as e:
            print("  [px] click err: %s" % str(e)[:80], flush=True)

        # poll token dari DOM
        dl = time.time() + wait
        while time.time() < dl and not tok:
            time.sleep(1.5)
            try:
                vals = page.eval_on_selector_all(
                    "textarea[name='cf-turnstile-response'],"
                    "input[name='cf-turnstile-response']",
                    "els => els.map(e => e.value || '')")
                tok = next((v for v in vals if v), "")
            except Exception:
                pass

        browser.close()

    if not tok:
        print("RESULT=FAIL (no token; clicked=%s %.0fs)" % (clicked, time.time() - t0),
              flush=True)
        sys.exit(1)

    with open(out_path, "w") as f:
        f.write(tok)
    print("RESULT=PASS token=%d (%.0fs, clicked=%s)" % (len(tok), time.time() - t0, clicked),
          flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
