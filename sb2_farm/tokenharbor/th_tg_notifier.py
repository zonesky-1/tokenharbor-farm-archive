#!/usr/bin/env python3
import os, sys, time, requests, json

BOT_TOKEN = "8602868943:AAHpygYDAwT7vYosz4i9LfsceGywXYZmLpk"
CHAT_ID = "7998819216"
KEYS_FILE = "/home/ubuntu/farm/tokenharbor/tokenharbor_keys.txt"
SENT_STATE = "/home/ubuntu/farm/tokenharbor/notified_keys.json"

def send_tg(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print("[-] TG Error:", e)

def get_keys():
    if not os.path.exists(KEYS_FILE): return []
    out = []
    with open(KEYS_FILE, "r", errors="ignore") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 4 and parts[3] == "ok" and parts[2].startswith("thk_live_"):
                out.append({"email": parts[0], "password": parts[1], "key": parts[2]})
    return out

def load_sent():
    if os.path.exists(SENT_STATE):
        try:
            return set(json.load(open(SENT_STATE)))
        except: pass
    return set()

def save_sent(sent_set):
    try:
        tmp_file = SENT_STATE + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(list(sent_set), f, indent=2)
        os.replace(tmp_file, SENT_STATE)
    except Exception as e:
        print("[-] save_sent error:", e)

print("[*] TokenHarbor Telegram Notifier Daemon started...")
while True:
    try:
        keys = get_keys()
        sent = load_sent()
        unsent = [k for k in keys if k["email"] not in sent]

        # Kirim per batch 5 akun
        while len(unsent) >= 1:
            batch = unsent[:5]
            unsent = unsent[5:]
            
            total_farmed = len(keys)
            batch_len = len(batch)
            msg_lines = [
                f"🎉 <b>[FARM REPORT] +{batch_len} Akun TokenHarbor Ready!</b>",
                f"📊 <b>Total Target:</b> {total_farmed}/1000 Akun\n"
            ]
            for idx, acc in enumerate(batch, 1):
                msg_lines.append(f"<b>{idx}. Email:</b> <code>{acc['email']}</code>")
                msg_lines.append(f"   <b>Pass:</b> <code>{acc['password']}</code>")
                msg_lines.append(f"   <b>API Key:</b> <code>{acc['key']}</code>\n")
                sent.add(acc['email'])

            send_tg("\n".join(msg_lines))
            save_sent(sent)
            time.sleep(2)

    except Exception as e:
        print("[-] Loop error:", e)

    time.sleep(10)
