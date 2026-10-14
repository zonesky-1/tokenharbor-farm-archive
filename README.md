# TOKENHARBOR FARM COMPLETE ARCHIVE & BACKUP
**Tanggal Backup:** 14 Oktober 2026
**Status:** ALL WORKERS STOPPED & CLEANED (Shutdown Complete)

---

## 1. Ringkasan Hasil Harvest
- **Total Akun/Key Valid & Live:** 1,051 API Keys (`thk_live_...`)
- **Total Keys Terdaftar di 9Router Cache:** 1,105 Keys
- **Total Keys Tervalidasi Telegram Notifier:** 1,048 Keys
- **Format Key:** `thk_live_xxxxxxxx...`

---

## 2. Struktur Folder Backup
```
tokenharbor_backup_complete/
├── keys_and_data/
│   ├── valid_live_keys.txt        # 1,051 live keys (email|password|key|status)
│   ├── api_keys_only.txt          # 1,051 raw API keys (1 per baris)
│   ├── valid_keys_1051.json       # JSON lengkap 1,051 keys
│   ├── 9r_registered_keys.json    # Dump sinkronisasi ke 9Router
│   └── 9r_keys_dump.json          # Dump backup database 9Router
│
├── sb2_farm/
│   ├── tokenharbor/               # Script worker inti TokenHarbor di SB2
│   │   ├── tokenharbor.py         # Engine register, camoufox bypass, harvest key
│   │   ├── auto_farm_loop.py      # Worker loop & process orchestrator
│   │   ├── th_tg_notifier.py      # Notifier Telegram real-time
│   │   ├── refill_clean_pool.py   # Pool rotasi proxy
│   │   ├── install.sh             # Setup dependency
│   │   └── tokenharbor_keys.txt   # Raw harvest log lengkap (12.6k lines)
│   ├── turnstile-solver-x/        # Cloudflare Turnstile Solver stack
│   │   ├── solve_turnstile.py     # Turnstile solver driver (0x4AAAAAADBuC8Knz1EJZx9-)
│   │   ├── ts_engine.py           # Engine solver
│   │   └── sk_finder.py           # Sitekey extractor
│   └── systemd_units/             # Konfigurasi service systemd SB2
│       ├── syad-th-farm.service   # Multi-worker unit (4 workers)
│       ├── syad-th-notif.service  # Notifier service unit
│       ├── th-refill.timer        # Timer auto refill proxy
│       └── th-refill.service      # Service auto refill
│
└── local_scripts/                 # Script sinkronisasi & proxy scanner lokal VPS
    ├── auto_sync_9router.py       # Auto sync SB2 keys -> 9Router VM
    ├── run_th_sync_9router.sh     # Watchdog bash script
    ├── th_harvest.py              # Harvester alternatif lokal
    └── scan_*.py                  # Scanner proxy HTTPS/US/SG
```

---

## 3. Catatan Maintenance & Restore
- Jika di masa depan ingin menjalankan lagi:
  1. Restore folder `tokenharbor` dan `turnstile-solver-x` ke remote sandbox / server.
  2. Setup environment via `install.sh`.
  3. Aktifkan service systemd `syad-th-farm.service` atau jalankan via `./auto_farm_loop.py`.
- Semua worker di SB2 (100.81.10.96) dan local VPS saat ini sudah dimatikan total (systemctl disabled & processes killed).
