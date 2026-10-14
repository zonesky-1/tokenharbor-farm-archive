#!/usr/bin/env python3
import os, sys, time, random, subprocess, signal, threading
from concurrent.futures import ThreadPoolExecutor

PROXY_FILE = "/home/ubuntu/farm/proxyfarm/th_clean_verified.txt"
VENV_PY = "/home/ubuntu/farm/venv/bin/python"
SCRIPT = "/home/ubuntu/farm/tokenharbor/tokenharbor.py"
NUM_WORKERS = 4

def kill_proc_tree(p):
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except Exception:
        pass

# ── THREAD-SAFE ROTASI QUEUE (ROUND-ROBIN DENGAN JEDA PENUH) ──
class RotatingProxyManager:
    def __init__(self, proxy_file):
        self.proxy_file = proxy_file
        self.lock = threading.Lock()
        self.available_queue = []
        self.used_history = []
        self.cycle_count = 0
        self.reload_pool()

    def reload_pool(self):
        try:
            with open(self.proxy_file) as pf:
                lines = [l.strip() for l in pf if l.strip() and not l.startswith("#")]
            # Acak urutan awal siklus
            random.shuffle(lines)
            self.available_queue = lines
            self.used_history = []
            print(f"[PROXY-MANAGER] Pool di-load: {len(self.available_queue)} IP siap rotasi (Siklus #{self.cycle_count + 1})", flush=True)
        except Exception as e:
            print(f"[PROXY-MANAGER] Gagal reload pool: {e}", flush=True)

    def get_proxy(self, worker_id):
        with self.lock:
            # Jika antrean habis, berarti SEMUA IP sudah dipakai 1x (Siklus selesai)
            if not self.available_queue:
                self.cycle_count += 1
                print(f"\n[PROXY-MANAGER] 🔄 SEMUA {len(self.used_history)} IP SUDAH DIPAKAI 1x! Masuk Siklus #{self.cycle_count + 1} (Jeda cooldown selesai)...\n", flush=True)
                # Reload ulang pool segar (menyingkirkan yang dibakar)
                self.reload_pool()

            if not self.available_queue:
                return ""

            # Ambil 1 IP dari depan antrean (pop) -> IP ini gak bakal kepake lagi oleh worker manapun sampai seluruh antrean habis
            px = self.available_queue.pop(0)
            self.used_history.append(px)
            remaining = len(self.available_queue)
            if remaining % 500 == 0 or remaining < 10:
                print(f"[PROXY-MANAGER] IP terpakai: {len(self.used_history)} | Sisa dalam siklus: {remaining}", flush=True)
            return px

proxy_mgr = RotatingProxyManager(PROXY_FILE)

def cleanup_tmp_loop():
    """Bersihkan sisa folder playwright di /tmp agar disk tidak penuh (ENOSPC)."""
    import glob, shutil
    while True:
        try:
            now = time.time()
            for pat in ["/tmp/playwright_*", "/tmp/playwright-artifacts*"]:
                for d in glob.glob(pat):
                    try:
                        # Hapus folder temp yang umurnya > 3 menit
                        if os.path.exists(d) and (now - os.path.getmtime(d) > 180):
                            if os.path.isdir(d):
                                shutil.rmtree(d, ignore_errors=True)
                            else:
                                os.remove(d)
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(60)

threading.Thread(target=cleanup_tmp_loop, daemon=True).start()


def run_worker(worker_id):
    time.sleep(worker_id * 3)
    while True:
        cmd = [VENV_PY, SCRIPT, "--count", "1", "--fast", "--label", f"w{worker_id}"]
        p = None
        child_env = dict(os.environ)
        
        # Ambil IP eksklusif dari queue (dijamin belum kepake di siklus ini)
        px = proxy_mgr.get_proxy(worker_id)
        if px:
            child_env["BROWSER_PROXY"] = px
            child_env["TURNSTILE_PROXY"] = px

        try:
            if px:
                print(f"[W{worker_id}] via proxy {px.split("@")[-1]}", flush=True)
            else:
                print(f"[W{worker_id}] via direct IP (pool proxy kosong)", flush=True)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, preexec_fn=os.setsid, env=child_env)
            hit_ratelimit = False
            try:
                stdout, _ = p.communicate(timeout=120)
                try:
                    with open(f"/tmp/th_w{worker_id}.log", "a") as lf:
                        lf.write("===== RESULT =====\n" + (stdout or "") + "\n")
                except Exception:
                    pass
                if "ratelimited" in (stdout or ""):
                    hit_ratelimit = True
                if px and any(k in (stdout or "") for k in ("blocked", "ratelimited", "dead_proxy")):
                    # IP kena block signup -> burn: catat + hapus dari clean pool
                    host = px.split("@")[-1]
                    try:
                        with open("/home/ubuntu/farm/proxyfarm/burnt.txt", "a") as bf:
                            bf.write(host + "\n")
                        with open(PROXY_FILE) as pf:
                            plines = pf.readlines()
                        with open(PROXY_FILE, "w") as pf:
                            pf.writelines(l for l in plines if l.strip() and host not in l)
                        print(f"[W{worker_id}] BURNED {host}", flush=True)
                    except Exception as _be:
                        print(f"[W{worker_id}] burn err: {_be}", flush=True)
                for line in (stdout or "").splitlines():
                    if any(k in line for k in ("SAVED:", "[signup]", "[api key]", "=== akun")):
                        print(f"[W{worker_id}] {line}", flush=True)
            except subprocess.TimeoutExpired:
                print(f"[W{worker_id}] Timeout 120s, killing process tree...", flush=True)
                kill_proc_tree(p)
                try:
                    out2, _ = p.communicate(timeout=5)
                    with open(f"/tmp/th_w{worker_id}.log", "a") as lf:
                        lf.write("===== TIMEOUT KILLED =====\n" + (out2 or "") + "\n")
                except Exception:
                    pass
                try: p.wait(timeout=5)
                except Exception: pass
        except Exception as e:
            print(f"[W{worker_id}] Err: {e}", flush=True)
            if p:
                kill_proc_tree(p)

        if hit_ratelimit:
            print(f"[W{worker_id}] IP Ratelimited -> Ganti proxy dari antrean...", flush=True)
            time.sleep(2)
        else:
            time.sleep(2)

def main():
    print(f"=== TOKENHARBOR AUTO-FARM LOOP (ROUND-ROBIN ROTATION QUEUE) ===", flush=True)
    print(f"Workers: {NUM_WORKERS} | Pool: 10k+ HTTPS Verified Proxies", flush=True)
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        for i in range(1, NUM_WORKERS + 1):
            executor.submit(run_worker, i)

if __name__ == "__main__":
    main()
