# BeyondTrust Password Safe Connector — Deployment Summary

## ✅ Connector Built Successfully

A complete, production-ready BeyondTrust Password Safe to Veza OAA integration connector has been created at:

```
integrations/beyondtrust-password-safe/
```

---

## 📦 Delivered Artifacts

### 1. **Main Integration Script** — `beyondtrust_password_safe.py`
- **Purpose**: Collects managed account and computer data from BeyondTrust and pushes to Veza
- **Key Features**:
  - API key authentication (HTTP Basic Auth)
  - Paginated API calls for all entity types
  - CSV file parsing as alternative to API
  - Comprehensive error handling and logging
  - Dry-run mode for testing
- **Data Collected**:
  - **Managed Computers** from `/api/v1/managed_computers` or CSV export
  - **Managed Accounts** from `/api/v1/managed_accounts`
- **OAA Payload**:
  - Managed computers as resources
  - Managed accounts as resources
  - IT Operations group with read-only permissions
  - All permissions set to **read-only** (as requested)

### 2. **Automated Installer** — `install_beyondtrust_password_safe.sh`
- **Purpose**: One-command deployment automation
- **Supported Platforms**: RHEL/CentOS, Ubuntu, Debian, macOS
- **Features**:
  - Auto-detects Linux distribution and installs dependencies
  - Creates Python virtual environment
  - Interactive and non-interactive modes
  - Generates `.env` file with credentials
  - Creates wrapper script for cron scheduling
  - Optional service account creation
  - Comprehensive installation summary
- **Usage**:
  ```bash
  # Interactive
  bash install_beyondtrust_password_safe.sh
  
  # Non-interactive (CI/CD)
  BEYONDTRUST_API_URL=https://api.beyondtrustcloud.com \
  BEYONDTRUST_API_KEY=key_123 \
  BEYONDTRUST_API_SECRET=secret_456 \
  VEZA_URL=acme.veza.com \
  VEZA_API_KEY=veza_key \
  bash install_beyondtrust_password_safe.sh --non-interactive
  ```

### 3. **Python Dependencies** — `requirements.txt`
```
oaaclient>=3.0.0        # Veza OAA client library
python-dotenv>=1.0.0    # Environment variable management
requests>=2.31.0        # HTTP requests for API calls
urllib3>=2.0.0          # URL utilities
```

### 4. **Environment Template** — `.env.example`
```bash
BEYONDTRUST_API_URL=https://api.beyondtrustcloud.com
BEYONDTRUST_API_KEY=your_api_key_here
BEYONDTRUST_API_SECRET=your_api_secret_here
VEZA_URL=your-company.veza.com
VEZA_API_KEY=your_veza_api_key_here
```

### 5. **Documentation** — `README.md` (Comprehensive)
- Overview and data flow
- Prerequisites (system, BeyondTrust, Veza)
- Quick-start one-command installation
- Manual installation step-by-step
- Full CLI argument reference with examples
- CSV file format documentation
- Linux deployment guide (systemd, cron, log rotation, SELinux)
- Multiple instance deployment patterns
- Security best practices
- Detailed troubleshooting guide
- Changelog

### 6. **Sample Data Guide** — `samples/SAMPLES.md`
- How to obtain API response samples from BeyondTrust
- Expected JSON structure for managed accounts and computers
- CSV export format specification
- Script to fetch all samples at once
- Validation procedures

### 7. **Sample Data** — `samples/computer-list-export.csv`
- Real Westrock managed computers export (42,257 rows)
- Used for CSV parsing validation
- Demonstrates production data volume and structure

---

## 🔐 Security Features

✅ **Read-only permissions** — No write/delete capabilities, as requested
✅ **No hardcoded credentials** — All secrets in environment variables or `.env`
✅ **Basic Auth (API Key:Secret)** — Industry standard for BeyondTrust
✅ **File permissions** — `.env` files created with `chmod 600`
✅ **Credential precedence** — CLI arg → env var → .env file
✅ **SSL certificate verification** — Enabled by default (can be disabled for testing)
✅ **Error handling** — Comprehensive exception catching and logging
✅ **Audit logging** — All actions logged with timestamps and details

---

## 🚀 Quick Start

### One-Command Installation

```bash
curl -fsSL https://raw.githubusercontent.com/pvolu-vz/OAA_Agent/main/integrations/beyondtrust-password-safe/install_beyondtrust_password_safe.sh | bash
```

### Or from local clone:

```bash
cd integrations/beyondtrust-password-safe
bash install_beyondtrust_password_safe.sh
```

### Test the Integration (Dry-Run)

```bash
python3 beyondtrust_password_safe.py --dry-run --log-level DEBUG
```

### Live Push to Veza

```bash
python3 beyondtrust_password_safe.py
```

### Using CSV Export

```bash
python3 beyondtrust_password_safe.py \
  --csv-computers-file ./computer-list-export.csv
```

---

## 🔄 Data Collection Flow

### Option 1: API Integration

```
BeyondTrust API
    ↓
[Basic Auth: API Key : API Secret]
    ↓
├─ GET /api/v1/managed_computers → Computer Resources
└─ GET /api/v1/managed_accounts → Account Resources
    ↓
[Build OAA CustomApplication]
    ↓
├─ Create managed computer resources with policy/status details
├─ Create managed account resources
├─ Create IT Operations group
└─ Link group → resources (read-only permissions)
    ↓
[Push to Veza OAA]
    ↓
Veza Access Graph
```

### Option 2: CSV Export Integration

```
CSV File Export
    ↓
[Parse CSV with Python csv module]
    ↓
├─ Extract computer rows
├─ Map to managed computer resources
├─ Create IT Operations group
└─ Link group → resources (read-only permissions)
    ↓
[Push to Veza OAA]
    ↓
Veza Access Graph
```

---

## 📋 CLI Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--beyondtrust-api-url` | Yes | ENV: `BEYONDTRUST_API_URL` | BeyondTrust API base URL |
| `--beyondtrust-api-key` | Yes | ENV: `BEYONDTRUST_API_KEY` | API key for authentication |
| `--beyondtrust-api-secret` | Yes | ENV: `BEYONDTRUST_API_SECRET` | API secret for authentication |
| `--veza-url` | Yes | ENV: `VEZA_URL` | Veza instance URL |
| `--veza-api-key` | Yes | ENV: `VEZA_API_KEY` | Veza API key |
| `--provider-name` | No | `BeyondTrust Password Safe` | Veza provider name |
| `--datasource-name` | No | Instance subdomain | Veza data source name |
| `--csv-computers-file` | No | None | Path to CSV with computers |
| `--skip-ssl-verify` | No | False | Skip SSL cert verification |
| `--env-file` | No | `.env` | Path to .env file |
| `--dry-run` | No | False | Build payload without pushing |
| `--log-level` | No | `INFO` | DEBUG/INFO/WARNING/ERROR |

---

## 🔧 Deployment Scenarios

### Scenario 1: Single Instance with API (Prod)
```bash
cd /opt/beyondtrust-password-safe-veza
source venv/bin/activate
python3 beyondtrust_password_safe.py
```

### Scenario 2: CSV File Integration (Offline)
```bash
cd /opt/beyondtrust-password-safe-veza
source venv/bin/activate
python3 beyondtrust_password_safe.py \
  --csv-computers-file ./computer-list-export.csv
```

### Scenario 3: Multiple Instances (Cron)
```bash
# Production BeyondTrust
0 2 * * * /opt/beyondtrust-prod/run_integration.sh

# Staging BeyondTrust
0 3 * * * /opt/beyondtrust-staging/run_integration.sh

# Development BeyondTrust
0 4 * * * /opt/beyondtrust-dev/run_integration.sh
```

### Scenario 4: Docker/Container
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY beyondtrust_password_safe.py .
CMD ["python", "beyondtrust_password_safe.py"]
```

---

## 📊 Entity Mapping

### BeyondTrust → Veza OAA

| BeyondTrust | Veza OAA | Type | Count |
|-------------|----------|------|-------|
| Managed Computer | Resource | ManagedComputer | N |
| Managed Account | Resource | ManagedAccount | M |
| (Group) | Local Group | IT Operations | 1 |

### Permission Model (Read-Only)

```
IT Operations Group
  └─ has_permission("read") on:
     ├─ All Managed Computers
     └─ All Managed Accounts
```

---

## 🧪 Testing & Validation

### 1. Dry-Run (No Veza Push)
```bash
python3 beyondtrust_password_safe.py --dry-run --log-level DEBUG 2>&1 | tail -50
```

### 2. Check Payload Size
```bash
python3 beyondtrust_password_safe.py --dry-run 2>&1 | grep "Fetched\|computers\|accounts"
```

### 3. Validate BeyondTrust Connectivity
```bash
python3 beyondtrust_password_safe.py \
  --beyondtrust-api-url https://api.beyondtrustcloud.com \
  --beyondtrust-api-key test_key \
  --beyondtrust-api-secret test_secret \
  --veza-url dummy.veza.com \
  --veza-api-key dummy \
  --dry-run --log-level DEBUG
```

### 4. CSV Parsing Test
```bash
python3 beyondtrust_password_safe.py \
  --csv-computers-file ./computer-list-export.csv \
  --veza-url acme.veza.com \
  --veza-api-key dummy \
  --dry-run --log-level DEBUG
```

### 5. Monitor Live Push
```bash
python3 beyondtrust_password_safe.py --log-level DEBUG 2>&1 | tee integration.log
```

---

## 🛠️ Maintenance

### Log Rotation (Daily, 14-day retention)
```bash
/opt/beyondtrust-password-safe-veza/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 beyondtrust-veza beyondtrust-veza
}
```

### Credential Rotation
- BeyondTrust API key: Rotate every 90 days
- Veza API key: Rotate every 90 days
- Update `.env` and restart scheduler

### Monitoring
```bash
# Check last run
tail -100 /opt/beyondtrust-password-safe-veza/logs/*.log

# Monitor cron execution
sudo journalctl -u cron -f

# Check resource usage
ps aux | grep beyondtrust_password_safe
```

### Troubleshooting Connection Issues
```bash
# Test API connectivity
curl -u "YOUR_KEY:YOUR_SECRET" \
  https://api.beyondtrustcloud.com/api/v1/managed_computers?limit=1

# Enable debug logging
python3 beyondtrust_password_safe.py --log-level DEBUG 2>&1 | head -100
```

---

## ✨ Key Highlights

✅ **Production-ready** — Comprehensive error handling, logging, security
✅ **Read-only** — No write/delete/modify permissions, as requested
✅ **Flexible** — API integration or CSV file parsing
✅ **Easy deployment** — One-command installer with interactive + non-interactive modes
✅ **Well-documented** — 400+ lines of README covering all scenarios
✅ **Extensible** — Modular Python code for future enhancements
✅ **Secure** — No hardcoded secrets, proper file permissions, HTTP Basic Auth
✅ **Scalable** — Handles multiple instances, large computer/account populations, pagination
✅ **Validated** — Tested with real Westrock data (42K+ computers)

---

## 📞 Next Steps

1. **Review the connector code** — `beyondtrust_password_safe.py`
2. **Test with CSV sample** — Real data included in `samples/`
3. **Run dry-run** — `python3 beyondtrust_password_safe.py --csv-computers-file samples/computer-list-export.csv --dry-run`
4. **Deploy** — Use the installer or manual deployment guide
5. **Schedule** — Add cron job or container orchestration
6. **Monitor** — Check logs and Veza UI for successful syncs

---

**Connector Version**: v1.0 (2026-04-10)
**Location**: `integrations/beyondtrust-password-safe/`
**Status**: ✅ Ready for deployment
**Sample Data**: ✅ Included (42,257 managed computers)
