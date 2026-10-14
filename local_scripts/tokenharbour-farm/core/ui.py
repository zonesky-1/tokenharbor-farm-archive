"""core.ui — tampilan CLI: banner, header, garis, tabel sederhana."""
import os

WIDTH = 64


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def line(char="-", width=WIDTH):
    print(char * width, flush=True)


def banner():
    clear()
    print()
    line("=")
    print("        🌾  T O K E N H A R B O U R   F A R M  🌾")
    print("        All-in-One: farm akun + verifikasi + import")
    line("=")
    print("  Telegram     : @Ortseam22  — cuma pecut AI buat")
    print("                 ngerombak program yang udah ada 😄")
    print("  Source asli  : https://github.com/RanzMods/token-harbor")
    line("=")


def header(text):
    print()
    line()
    print(f"  {text}")
    line()


def table(rows, headers):
    """Cetak tabel sederhana dengan auto-width per kolom."""
    if not rows:
        print("  (kosong)", flush=True)
        return
    cols = len(headers)
    widths = [len(str(h)) for h in headers]
    str_rows = []
    for row in rows:
        cells = [str(c) for c in row][:cols]          # buang kelebihan kolom
        cells += [""] * (cols - len(cells))           # isi kolom kurang
        str_rows.append(cells)
        for i in range(cols):
            widths[i] = max(widths[i], len(cells[i]))
    fmt = "  " + "  ".join("{:<%d}" % w for w in widths)
    print(fmt.format(*headers), flush=True)
    print("  " + "  ".join("-" * w for w in widths), flush=True)
    for cells in str_rows:
        print(fmt.format(*cells), flush=True)
