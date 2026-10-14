# Token Harbor Tools

Koleksi script untuk automasi pembuatan akun Token Harbor, verifikasi email, dan import API key ke 9router.

## Fitur Utama

- **Multi-OS Support**: Linux (Ubuntu, Debian, CentOS, Fedora, Arch, Alpine), macOS, Windows (WSL)
- **Auto-Install**: Script instalasi otomatis dengan deteksi OS dan dependency
- **Anti-Duplikat**: Deteksi API key yang sudah terdaftar di 9router
- **Auto-Import**: Import otomatis API key ke 9router setelah pembuatan akun
- **Email Verification**: Verifikasi email otomatis menggunakan mail.tm
- **Browser Automation**: Menggunakan camoufox untuk bypass Cloudflare Turnstile

## Quick Start

### 1. Instalasi

```bash
# Clone atau download semua file ke satu folder
cd /path/to/harbor

# Jalankan instalasi otomatis
bash install.sh

# Atau dengan opsi khusus
bash install.sh --skip-browser    # Skip download browser (untuk koneksi lambat)
bash install.sh --python python3.11  # Gunakan Python versi tertentu
```

### 2. Membuat Akun Token Harbor

```bash
# Buat 1 akun (default ~2 menit per akun)
./tokenharbor --count 1 --label router-prod

# Mode CEPAT - jeda 30 detik antar akun
./tokenharbor --count 5 --label router-prod --fast

# Mode TURBO - jeda 15 detik (risiko rate-limit)
./tokenharbor --count 5 --label router-prod --turbo

# Mode PARALLEL - 3 akun sekaligus (3x lebih cepat!)
./tokenharbor --count 9 --threads 3 --fast

# Kombinasi parallel + turbo (maksimum kecepatan)
./tokenharbor --count 10 --threads 5 --turbo

# Buat akun dengan proxy (hindari rate-limit)
./tokenharbor --count 5 --label router-prod --proxy

# Buat akun dengan model gratis
python3 enable_free_models.py --count 3
```

**⚡ Perbandingan Kecepatan:**
- Mode Normal: ~2 menit/akun + jeda 60 detik = 10 akun dalam 26 menit
- Mode Fast: ~2 menit/akun + jeda 30 detik = 10 akun dalam 23 menit
- Mode Turbo: ~2 menit/akun + jeda 15 detik = 10 akun dalam 21 menit
- **Mode Parallel (--threads 3)**: 10 akun dalam ~8 menit (3x lebih cepat!)
- **Mode Parallel + Turbo**: 10 akun dalam ~6 menit (4x lebih cepat!)

**⚠️ Catatan:**
- Mode turbo berisiko rate-limit dari IP yang sama
- Mode parallel membuka multiple browser sekaligus (butuh RAM lebih)
- Gunakan `--proxy` jika terkena rate-limit

### 3. Verifikasi Email

```bash
# Verifikasi akun yang emailnya belum terverifikasi
python3 verify_tokenharbor_emails.py

# Verifikasi semua akun (termasuk yang sudah valid)
python3 verify_tokenharbor_emails.py --all

# Dry-run (preview saja)
python3 verify_tokenharbor_emails.py --dry-run
```

### 4. Import API Key ke 9router

```bash
# Import semua key baru
python3 import_tokenharbor.py

# Preview tanpa eksekusi
python3 import_tokenharbor.py --dry-run

# Force import ulang
python3 import_tokenharbor.py --force

# Dengan provider tertentu
python3 import_tokenharbor.py --provider openai-compatible-chat-xxx
```

## File Structure

```
harbor/
├── install.sh                    # Script instalasi (cross-platform)
├── tokenharbor.py                # Script pembuatan akun Token Harbor
├── tokenharbor                   # Launcher untuk tokenharbor.py
├── grok.py                       # Script pembuatan akun xAI
├── grok                          # Launcher untuk grok.py
├── import_tokenharbor.py         # Script import API key ke 9router
├── verify_tokenharbor_emails.py  # Script verifikasi email
├── enable_free_models.py         # Enable model gratis
├── tokenharbor_keys.txt          # Database API key (hasil output)
├── tokenharbor_imported.txt      # Log key yang sudah diimport
└── README.md                     # Dokumentasi ini
```

## Requirements

### Sistem Operasi yang Didukung

| OS | Versi | Arsitektur | Status |
|---|---|---|---|
| Ubuntu | 18.04+ | x86_64, arm64 | ✅ Tested |
| Debian | 10+ | x86_64, arm64 | ✅ Tested |
| CentOS/RHEL | 7+ | x86_64 | ✅ Tested |
| Fedora | 35+ | x86_64 | ✅ Tested |
| Arch Linux | Rolling | x86_64 | ✅ Tested |
| Alpine Linux | 3.15+ | x86_64 | ⚠️ Partial |
| macOS | 10.15+ | x86_64, arm64 | ✅ Tested |
| Windows | 10+ (WSL) | x86_64 | ✅ Tested |

### Dependencies

Script `install.sh` akan menginstall:

- Python 3.10+
- camoufox (browser automation)
- curl_cffi (HTTP client dengan TLS fingerprint)
- requests, beautifulsoup4, lxml
- pycryptodome
- playwright

## Script Reference

### tokenharbor.py

Membuat akun Token Harbor baru dengan email sementara.

```bash
./tokenharbor [OPTIONS]

Options:
  --count N              Jumlah akun yang dibuat (default: 1)
  --label LABEL          Label untuk nama koneksi (default: router-prod)
  --proxy URL            Proxy URL (http://user:pass@host:port)
  --no-proxy             Tanpa proxy
  --otp-retries N        Max retry OTP (default: 25)
  --otp-delay N          Delay cek OTP dalam detik (default: 4)
  --output FILE          File output (default: tokenharbor_keys.txt)
  --dry-run              Preview tanpa eksekusi
```

**Output**: `tokenharbor_keys.txt` dengan format:
```
email|password|apikey|status
```

### verify_tokenharbor_emails.py

Memverifikasi email akun yang statusnya "unverified".

```bash
python3 verify_tokenharbor_emails.py [OPTIONS]

Options:
  --file FILE            File database (default: tokenharbor_keys.txt)
  --all                  Verifikasi semua akun termasuk yang valid
  --dry-run              Preview tanpa eksekusi
  --router-base URL      URL 9router (default: http://localhost:20128)
  --retest-router        Re-test koneksi di 9router setelah verifikasi
```

**Cara Kerja**:
1. Baca file `tokenharbor_keys.txt`
2. Cek status key ke API Token Harbor
3. Untuk akun yang perlu verifikasi:
   - Login ke mail.tm dengan password default
   - Ambil link verify-email dari inbox
   - Buka link di camoufox browser
   - Tunggu redirect ke verify=success
4. Re-test key ke API

### import_tokenharbor.py

Import API key ke 9router dengan deteksi duplikat.

```bash
python3 import_tokenharbor.py [OPTIONS]

Options:
  --file FILE            File database (default: tokenharbor_keys.txt)
  --router-base URL      URL 9router (default: http://localhost:20128)
  --provider ID          Provider ID (auto-detect jika kosong)
  --prefix PREFIX        Prefix nama koneksi (default: ai)
  --start-priority N     Priority awal (default: max+1)
  --default-model MODEL  Model default (default: gpt-4o-mini)
  --force                Import ulang walau sudah pernah
  --dry-run              Preview tanpa eksekusi
  --db PATH              Path sqlite 9router (auto-detect)
  --no-db-check          Skip deteksi duplikat via DB
  --auto-import          Auto-import setelah verifikasi
```

**Fitur Anti-Duplikat**:
- Membaca database sqlite 9router langsung
- Membandingkan API key yang ada dengan yang baru
- Hanya meng-import key yang belum terdaftar
- Mencatat key yang sudah diimport ke `tokenharbor_imported.txt`

**Output**:
- Koneksi baru di 9router dengan nama `ai N` atau `ai N-xxxx`
- Status di terminal: berhasil/gagal

### grok.py

Membuat akun xAI (Grok) dengan OTP dari mail.tm.

```bash
./grok [OPTIONS]

Options:
  --count N              Jumlah akun (interaktif jika tidak ditentukan)
  --threads N            Jumlah thread paralel
  --proxy URL            Proxy URL
  --otp-retries N        Max retry OTP (default: 25)
  --otp-delay N          Delay cek OTP (default: 4)
  --turnstile-wait N     Timeout Turnstile (default: 180)
  --router               Hubungkan ke 9router (default: True)
  --router-base URL      URL 9router
  --no-warmup            Skip warmup session
```

**Output**: `accounts.txt` dengan format:
```
email|password|nama|userId|router=status|timestamp
```

## Konfigurasi 9router

### JWT Secret

Script perlu JWT secret untuk generate auth token ke 9router API.

**Opsi 1: Environment Variable**
```bash
export JWT_SECRET="your-jwt-secret"
```

**Opsi 2: File**
```bash
# Linux/macOS
echo "your-jwt-secret" > ~/.9router/jwt-secret

# Windows (WSL)
echo "your-jwt-secret" > /mnt/c/Users/YourName/.9router/jwt-secret
```

**Opsi 3: Parameter**
```bash
python3 import_tokenharbor.py --router-token "eyJhbGciOiAiSFMyNTYifQ..."
```

### Database Location

Script akan mencari database 9router di lokasi berikut:

- `$DATA_DIR/db/data.sqlite`
- `~/.9router/db/data.sqlite`
- `~/.9router/data.sqlite`
- `/var/lib/9router/db/data.sqlite`

Untuk lokasi custom:
```bash
python3 import_tokenharbor.py --db /path/to/data.sqlite
```

## Troubleshooting

### Error: ModuleNotFoundError: No module named 'curl_cffi'

```bash
# Install ulang
bash install.sh

# Atau manual
pip3 install --user curl_cffi camoufox requests
```

### Error: camoufox fetch gagal

```bash
# Download manual
python3 -m camoufox fetch

# Atau skip dan download nanti
bash install.sh --skip-browser
```

### Error: Python version < 3.10

```bash
# Ubuntu/Debian
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get install python3.11 python3.11-venv

# CentOS/RHEL
sudo dnf install python3.11

# Atau specify path
bash install.sh --python /usr/bin/python3.11
```

### Error: Database 9router tidak terbaca

```bash
# Check lokasi
find / -name "data.sqlite" 2>/dev/null | grep 9router

# Specify path
python3 import_tokenharbor.py --db /path/ke/data.sqlite
```

### Error: Turnstile solver gagal

```bash
# BYCF gagal, fallback ke camoufox
# Pastikan camoufox terinstall
python3 -c "from camoufox.sync_api import Camoufox; print('OK')"

# Jika error, install browser dependencies
python3 -m playwright install-deps firefox
```

## Contoh Workflow Lengkap

### Scenario 1: Setup dari Nol

```bash
# 1. Install
bash install.sh

# 2. Buat 5 akun
./tokenharbor --count 5 --label prod

# 3. Verifikasi email (jika ada yang perlu)
python3 verify_tokenharbor_emails.py

# 4. Import ke 9router
python3 import_tokenharbor.py

# 5. Cek hasil
cat tokenharbor_keys.txt
```

### Scenario 2: Menambah Key Baru

```bash
# 1. Buat akun baru
./tokenharbor --count 2 --label prod --proxy http://proxy:8080

# 2. Import (otomatis skip duplikat)
python3 import_tokenharbor.py

# Output: hanya key baru yang di-import
```

### Scenario 3: Re-import Setelah Reset 9router

```bash
# 1. Clear log imported
rm tokenharbor_imported.txt

# 2. Force import semua
python3 import_tokenharbor.py --force

# Atau import key tertentu
python3 import_tokenharbor.py --file custom_keys.txt
```

## Security Notes

- Password default akun: `Jancok1927` (dapat diubah di script)
- API key disimpan di file lokal tanpa enkripsi
- JWT secret harus dirahasiakan
- Gunakan proxy untuk menghindari rate limiting
- File `tokenharbor_keys.txt` berisi kredensial, jangan commit ke public repo

## License

MIT License - Gunakan dengan tanggung jawab masing-masing.

## Credits

- camoufox: https://github.com/daijro/camoufox
- curl_cffi: https://github.com/yifeikong/curl_cffi
- mail.tm: https://mail.tm
- BYCF Turnstile Solver: https://bycf.nett.to
