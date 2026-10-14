# Agent Guidance for Harbor Scripts

## Overview
This project contains scripts for automating Token Harbor and xAI account creation, email verification, and API key import to 9router.

## Available Scripts

### 1. install.sh
Cross-platform installation script for all dependencies.

**Usage:**
```bash
bash install.sh                    # Full install
bash install.sh --skip-browser     # Skip browser download
bash install.sh --python python3.11 # Use specific Python version
```

### 2. tokenharbor.py / ./tokenharbor
Create Token Harbor accounts with temporary email.

**Usage:**
```bash
# Normal mode (~2 menit/akun)
./tokenharbor --count 3 --label router-prod

# Fast mode (jeda 30 detik)
./tokenharbor --count 5 --label router-prod --fast

# Turbo mode (jeda 15 detik)
./tokenharbor --count 5 --label router-prod --turbo

# Parallel mode (3x lebih cepat!)
./tokenharbor --count 9 --threads 3 --fast

# Dengan proxy
./tokenharbor --count 5 --proxy
```

**Output:** `tokenharbor_keys.txt` (email|password|apikey|status)

### 3. verify_tokenharbor_emails.py
Verify email for accounts with "unverified" status.

**Usage:**
```bash
python3 verify_tokenharbor_emails.py
python3 verify_tokenharbor_emails.py --all  # Verify all accounts
```

**Workflow:**
1. Read tokenharbor_keys.txt
2. Check API key status (200=valid, 403=unverified)
3. For unverified accounts: login to mail.tm, get verification link, open in browser
4. Retest key after verification

### 4. import_tokenharbor.py
Import API keys to 9router with duplicate detection.

**Usage:**
```bash
python3 import_tokenharbor.py
python3 import_tokenharbor.py --dry-run  # Preview only
python3 import_tokenharbor.py --force    # Force re-import
```

**Features:**
- Auto-detects 9router database location
- Filters out already connected keys
- Only imports new/unique keys
- Tracks imported keys in tokenharbor_imported.txt

### 5. grok.py / ./grok
Create xAI (Grok) accounts via console.x.ai.

**Usage:**
```bash
./grok  # Interactive mode
./grok --count 5 --threads 2
```

**Output:** `accounts.txt` (email|password|name|userId|status)

### 6. enable_free_models.py
Enable free models for Token Harbor accounts.

**Usage:**
```bash
python3 enable_free_models.py --count 3
```

## Database Locations
Scripts auto-detect 9router database:

- **Linux/macOS:**
  - `~/.9router/db/data.sqlite`
  - `~/.9router/data.sqlite`
  - `/var/lib/9router/db/data.sqlite`
  - `$DATA_DIR/db/data.sqlite`

- **Windows:**
  - `%APPDATA%\9router\data.sqlite`
  - `%LOCALAPPDATA%\9router\data.sqlite`

## JWT Secret Locations
For 9router authentication:

1. `export JWT_SECRET="your-secret"`
2. `~/.9router/jwt-secret` (Linux/macOS)
3. `%APPDATA%\9router\jwt-secret` (Windows)

## File Formats

### tokenharbor_keys.txt
```
email|password|apikey|status
example@mail.com|password123|thk_live_abc123|ok
test@mail.com|pass456||ratelimited
```

### accounts.txt (grok.py output)
```
email|password|name|userId|router=status|timestamp
```

### tokenharbor_imported.txt
```
md5hash_of_key1
md5hash_of_key2
```

## Common Issues & Solutions

### 1. ModuleNotFoundError: 'curl_cffi'
Run: `bash install.sh` or `pip install curl_cffi`

### 2. Python version < 3.10
Use: `bash install.sh --python python3.11`

### 3. Database not found
Specify: `python3 import_tokenharbor.py --db /path/to/data.sqlite`

### 4. Browser download fails
Use: `bash install.sh --skip-browser`

### 5. Turnstile solver fails
Script auto-falls back from BYCF to camoufox browser solution.

## Typical Workflow

1. **Setup:**
   ```bash
   bash install.sh
   ```

2. **Create accounts:**
   ```bash
   ./tokenharbor --count 5 --label prod
   ```

3. **Verify emails (if needed):**
   ```bash
   python3 verify_tokenharbor_emails.py
   ```

4. **Import to 9router:**
   ```bash
   python3 import_tokenharbor.py
   ```

## Notes for AI Agents

- Always check Python version >= 3.10 before running scripts
- Use `--dry-run` flag for preview without changes
- Scripts maintain state in text files (keys.txt, imported.txt)
- Duplicate detection is built-in to prevent double imports
- Error handling includes fallbacks for failed services
- Cross-platform support includes Linux, macOS, Windows (WSL)

## Verification Commands
After making changes, run these checks:

```bash
# Syntax check
python3 -m py_compile tokenharbor.py import_tokenharbor.py

# Help test
python3 import_tokenharbor.py --help
python3 verify_tokenharbor_emails.py --dry-run
```

## Security Notes
- API keys stored in plain text files
- Use proxy option for rate limiting avoidance
- Never commit tokenharbor_keys.txt to version control
- JWT secret should be kept secure
