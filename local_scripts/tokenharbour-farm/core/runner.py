"""core.runner — jalankan script lama via subprocess dengan output live.

Program lama dipanggil apa adanya (tidak dimodifikasi) sehingga tetap
jadi acuan valid. Output di-stream baris per baris ke terminal.
"""
import os
import subprocess
import sys

from core import paths


def _child_cmd(script_args):
    """Susun perintah untuk menjalankan script lama.

    - Normal : python -X utf8 <script> <args...>
    - Frozen : exe memanggil dirinya sendiri dengan flag internal --th-run;
      farm lalu mengeksekusi script via runpy (tanpa python terinstall).
    """
    head = [str(a) for a in script_args]
    if paths.FROZEN:
        return [sys.executable, "--th-run"] + head
    return [paths.python_exe(), "-X", "utf8"] + head


def run_stream(script_args, show_cmd=True):
    """Jalankan script python. script_args = list path/argumen.
    Return exit code."""
    cmd = _child_cmd(script_args)
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env["PYTHONUTF8"] = "1"
    if show_cmd:
        print(flush=True)
        print("  $ run: " + " ".join(str(a) for a in script_args), flush=True)
        print(flush=True)
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(paths.PROJECT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )
    except Exception as e:
        print(f"  !! Gagal menjalankan: {e}", flush=True)
        return -1

    try:
        for raw in proc.stdout:
            print("  | " + raw.rstrip(), flush=True)
        proc.wait()
    except KeyboardInterrupt:
        # user menekan Ctrl-C: pastikan proses anak ikut dimatikan
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        print("\n  [!] Dihentikan oleh user.", flush=True)
        return 130
    finally:
        # pastikan pipe stdout ditutup agar tidak bocor handle file
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass

    print(flush=True)
    if proc.returncode == 0:
        print("  [OK] Selesai tanpa error.", flush=True)
    else:
        print(f"  [!!] Selesai dengan exit code {proc.returncode}", flush=True)
    return proc.returncode
