# 🌾 TokenHarbour Farm

> Telegram: [@Ortseam22](https://t.me/Ortseam22) — tinggal pecat AI buat
> ngerombak program yang sudah ada · Source asli: <https://github.com/RanzMods/token-harbor>

Program **all-in-one interaktif** yang menggabungkan 5 script lama yang
terpisah menjadi satu CLI user-friendly. Tidak ada lagi flag CLI yang
harus dihafal — cukup jalankan program, lalu jawab pertanyaan yang muncul.

> ⚠️ Program lama di folder induk (`token-harbor-main/`) **tidak diubah
> sama sekali** dan tetap menjadi acuan valid. Program ini hanya
> memanggilnya sebagai mesin eksekusi via subprocess.

## Cara Pakai

Double-click **`start.bat`** (atau dari terminal):

```
cd tokenharbour-farm
start.bat
```

Maka muncul menu:

```
  Pilih tugas:
    1. 🌾 Farm akun baru (daftar + verifikasi + key siap pakai)
    2. ✉️  Verifikasi email akun yang belum verified
    3. 🔑 Cek validitas API key semua akun
    4. 📥 Import key ke 9router
    5. 🎁 Enable free models
    6. 📊 Lihat daftar akun & status
    0. Keluar
```

Setiap pilihan akan menanyakan parameter satu per satu dengan **default
yang bisa langsung di-Enter**, contoh menu [1]:

```
  Jumlah akun yang mau dibuat [1]:
  Label API key [router-prod]:
  Mode jeda antar akun
    1. Normal — jeda 60 detik (paling aman)
    2. Fast — jeda 30 detik   *
    3. Turbo — jeda 15 detik (risiko rate-limit)
  Pilih [1-3, Enter=2]:
  Proses paralel (threads) [1]:
  Gunakan web-proxy untuk hindari rate-limit per IP? [y/N]: n
  Mulai farm 1 akun (estimasi ~9 menit)? [Y/n]:
```

## Struktur Program

```
tokenharbour-farm/
├── start.bat              ← launcher (double-click ini)
├── farm.py                ← entry point + menu utama
├── README.md
└── core/
    ├── paths.py           ← lokasi script lama & file data
    ├── prompts.py         ← helper input interaktif (default & validasi)
    ├── ui.py              ← banner, header, tabel
    ├── runner.py          ← eksekusi script lama (output live streaming)
    ├── storage.py         ← baca/tampil tokenharbor_keys.txt
    └── tasks/
        ├── farming.py       → menjalankan run_chrome.py
        ├── verification.py  → menjalankan verify_tokenharbor_emails.py
        ├── keycheck.py      → tes API key langsung (read-only)
        ├── router_import.py → menjalankan import_tokenharbor.py
        └── free_models.py   → menjalankan enable_free_models.py
```

## Menambah Modul Baru

1. Buat fungsi `run()` di `core/tasks/<nama>.py`
2. Import di `farm.py`, tambahkan entri di list `MENU`

## Catatan Teknis

- **Output farm terpisah**: semua hasil ditulis di `tokenharbour-farm\output\`
  (`tokenharbor_keys.txt`, `tokenharbor_ready.txt`,
  `tokenharbor_imported.txt`). Proyek induk tidak pernah dimodifikasi.
- Script lama (mis. `run_chrome.py`) memang masih menulis sementara ke
  proyek induk karena tidak bisa diubah — setelah itu farm otomatis
  **menggabungkan (merge by email)** hasilnya ke `output\` milik farm,
  tanpa menimpa update status dari verifikasi.
- Python sebaiknya dari venv (butuh `curl_cffi`, `playwright`,
  `requests`). start.bat dan program otomatis mencari venv di folder
  farm, proyek induk, atau root repo — jika tidak ada, fallback ke
  Python sistem.
- Selalu dijalankan dengan `-X utf8` agar emoji/Unicode aman.
- WDAC: jangan jalankan `tokenharbor.py` langsung (Camoufox diblokir);
  farming lewat `run_chrome.py` yang pakai Chrome Playwright channel.

