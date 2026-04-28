# BeyondTrust Password Safe to Veza OAA Integration

## Overview

This integration script collects managed account and managed computer data from **BeyondTrust Password Safe** and pushes it to **Veza** via the Open Authorization API (OAA). The connector provides read-only access to:

- **Managed Accounts** — User accounts managed by BeyondTrust
- **Managed Computers** — Computers under BeyondTrust management
- **Account & Computer Details** — Policies, domains, status, and configuration information

All data flows through Veza's OAA model, enabling centralized visibility into privileged access management (PAM) and endpoint security across your organization.

---

## How It Works

The integration follows this flow:

1. **Authenticate** — Validates credentials with BeyondTrust API using API key and secret
2. **Fetch Entities** — Retrieves managed accounts and computers from BeyondTrust APIs
3. **Build Payload** — Constructs a Veza CustomApplication object with:
   - Managed computers as resources
   - Managed accounts as resources
   - IT Operations group with read-only access to all resources
4. **Push to Veza** — Sends the complete OAA payload to Veza for indexing and analysis
5. **Log Results** — Tracks metrics (resources discovered, permissions assigned, warnings)

---

## Prerequisites

### System Requirements
- **OS**: Linux (RHEL/CentOS, Ubuntu, Debian) or macOS
- **Python**: 3.8 or higher
- **Internet Access**: HTTPS connectivity to BeyondTrust and Veza instances
- **Disk Space**: ≥ 500 MB (for venv and logs)

### BeyondTrust Prerequisites
- Active BeyondTrust Password Safe or Vault instance
- API access enabled with API key and secret
- **Required API Endpoints**: 
  - `GET /api/v1/managed_accounts` (read-only)
  - `GET /api/v1/managed_computers` (read-only)

### Veza Prerequisites
- Active Veza instance with API access
- Valid API key with permissions to push OAA data
- Network connectivity from integration server to Veza

### Network Requirements
- Outbound HTTPS (port 443) to BeyondTrust: `api.beyondtrustcloud.com` or custom domain
- Outbound HTTPS (port 443) to Veza instance: `*.veza.com`
- Optional: firewall rules limiting access to service account IP

---

## Quick Start

### One-Command Installation (Interactive)

```bash
curl -fsSL https://raw.githubusercontent.com/pvolu-vz/OAA_Agent/main/integrations/beyondtrust-password-safe/install_beyondtrust_password_safe.sh | bash
```

The installer will:
1. Install system dependencies (Python 3, pip, git, curl)
2. Clone the integration repository
3. Create a Python virtual environment
4. Prompt for BeyondTrust and Veza credentials
5. Generate a `.env` file with configuration
6. Create a wrapper script for cron scheduling

---

## Manual Installation

### Step 1: Clone the Repository

```bash
# Clone the OAA Agent template
git clone https://github.com/pvolu-vz/OAA_Agent.git
cd OAA_Agent
```

### Step 2: Create Installation Directory

```bash
# Create dedicated installation directory
sudo mkdir -p /opt/beyondtrust-password-safe-veza
sudo chown $USER:$USER /opt/beyondtrust-password-safe-veza
cd /opt/beyondtrust-password-safe-veza
```

### Step 3: Set Up Python Virtual Environment

```bash
# Create venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r integrations/beyondtrust-password-safe/requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy the example .env
cp integrations/beyondtrust-password-safe/.env.example .env

# Edit .env with your credentials
nano .env
```

### Step 5: Test the Integration

```bash
# Dry-run (don't push to Veza)
python3 integrations/beyondtrust-password-safe/beyondtrust_password_safe.py --dry-run

# Live push
python3 integrations/beyondtrust-password-safe/beyondtrust_password_safe.py
```

---

## Usage

### CLI Arguments

```
python3 beyondtrust_password_safe.py [OPTIONS]

OPTIONS:
  --beyondtrust-api-url TEXT     BeyondTrust API base URL [required]
                                 Env: BEYONDTRUST_API_URL
                                 Format: https://api.beyondtrustcloud.com

  --beyondtrust-api-key TEXT     BeyondTrust API key [required]
                                 Env: BEYONDTRUST_API_KEY

  --beyondtrust-api-secret TEXT  BeyondTrust API secret [required]
                                 Env: BEYONDTRUST_API_SECRET

  --veza-url TEXT                Veza instance URL [required]
                                 Env: VEZA_URL
                                 Format: acme.veza.com or https://acme.veza.com

  --veza-api-key TEXT            Veza API key [required]
                                 Env: VEZA_API_KEY

  --provider-name TEXT           Veza provider name
                                 Default: BeyondTrust Password Safe
                                 Env: PROVIDER_NAME

  --datasource-name TEXT         Veza data source name
                                 Default: <instance-name>
                                 Env: DATASOURCE_NAME

  --csv-computers-file PATH      Path to CSV file with managed computers
                                 Alternative to API (optional)

  --skip-ssl-verify              Skip SSL certificate verification
                                 (NOT recommended for production)

  --env-file PATH                Path to .env file
                                 Default: .env

  --dry-run                      Build payload but skip push to Veza

  --log-level {DEBUG,INFO,WARNING,ERROR}
                                 Logging level
                                 Default: INFO

  --help                         Show help message
```

### Examples

#### Example 1: Basic Usage with Environment File

```bash
python3 beyondtrust_password_safe.py
```

Reads credentials from `.env` in current directory.

#### Example 2: Dry-Run Test

```bash
python3 beyondtrust_password_safe.py --dry-run --log-level DEBUG
```

Tests authentication and data collection without pushing to Veza.

#### Example 3: Using CSV Export

```bash
python3 beyondtrust_password_safe.py \
  --csv-computers-file ./computers-export.csv
```

Loads managed computer data from CSV instead of API.

#### Example 4: Custom Names

```bash
python3 beyondtrust_password_safe.py \
  --provider-name "ACME BeyondTrust" \
  --datasource-name "ACME Production PAM"
```

#### Example 5: Non-Interactive (CI/CD)

```bash
BEYONDTRUST_API_URL=https://api.beyondtrustcloud.com \
BEYONDTRUST_API_KEY=key123 \
BEYONDTRUST_API_SECRET=secret456 \
VEZA_URL=acme.veza.com \
VEZA_API_KEY=veza_key \
python3 beyondtrust_password_safe.py
```

---

## Deployment on Linux

### Create Service Account

```bash
# Create dedicated service account
sudo useradd -r -s /bin/bash -m -d /opt/beyondtrust-password-safe-veza beyondtrust-veza

# Set permissions
sudo chown -R beyondtrust-veza:beyondtrust-veza /opt/beyondtrust-password-safe-veza
sudo chmod 700 /opt/beyondtrust-password-safe-veza
sudo chmod 600 /opt/beyondtrust-password-safe-veza/.env
```

### Schedule with Cron

#### Example 1: Daily at 2 AM

```bash
# Edit crontab
sudo crontab -e -u beyondtrust-veza

# Add line:
0 2 * * * bash /opt/beyondtrust-password-safe-veza/run_integration.sh >> /opt/beyondtrust-password-safe-veza/logs/cron.log 2>&1
```

#### Example 2: Every 6 Hours

```bash
0 */6 * * * bash /opt/beyondtrust-password-safe-veza/run_integration.sh >> /opt/beyondtrust-password-safe-veza/logs/cron.log 2>&1
```

#### Example 3: Business Hours (9 AM - 5 PM)

```bash
0 9-17 * * 1-5 bash /opt/beyondtrust-password-safe-veza/run_integration.sh >> /opt/beyondtrust-password-safe-veza/logs/cron.log 2>&1
```

### Configure Log Rotation (RHEL/CentOS)

```bash
# Create logrotate config
sudo tee /etc/logrotate.d/beyondtrust-veza > /dev/null << 'EOF'
/opt/beyondtrust-password-safe-veza/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 beyondtrust-veza beyondtrust-veza
    sharedscripts
}
EOF

# Test logrotate
sudo logrotate -vf /etc/logrotate.d/beyondtrust-veza
```

### Configure Log Rotation (Ubuntu/Debian)

```bash
# Create logrotate config
sudo tee /etc/logrotate.d/beyondtrust-veza > /dev/null << 'EOF'
/opt/beyondtrust-password-safe-veza/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 beyondtrust-veza beyondtrust-veza
}
EOF
```

### SELinux Configuration (RHEL/CentOS)

If you see permission errors related to SELinux:

```bash
# Check SELinux status
getenforce

# If enforcing, allow venv access
sudo chcon -Rv -t user_home_t /opt/beyondtrust-password-safe-veza/

# Verify
ls -Z /opt/beyondtrust-password-safe-veza/
```

---

## CSV File Format

When using `--csv-computers-file`, the CSV should include the following columns (from BeyondTrust export):

```csv
Name,Status,Days Disconnected,Group Name,Assigned Policy,Current Applied Policy,Policy Status,Id,Last Connected,Computer,Adapter,Package Manager Version,Adapter Installation Status,Agent Installation Status,OS,Domain,Created On,Authorisation State,System Type,ArchivedOn
```

**Example:**
```csv
"001SQL","Connected","0","Windows Servers","Windows Server Policy - PRODUCTION v33","Windows Server Policy - PRODUCTION v33","OnAssignedPolicy","13a0ecef-f956-4a17-8b03-9a601792ee24","04/09/2026 03:13 PM","23.1.269.0","23.1.942.0","","ManualUpdates","ManualUpdates","Microsoft Windows Server 2012 Datacenter","westrock.com","07/25/2022 01:31 PM","Authorised","x64-based PC",""
```

---

## Security Considerations

### Credential Management

- **Never commit `.env` files to Git** — add to `.gitignore`
- **Rotate API keys regularly** — BeyondTrust and Veza keys should be rotated quarterly
- **Use a secrets manager** (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) in production
- **Implement least privilege** — BeyondTrust API credentials should only have read access

### File Permissions

```bash
# Protect .env file
chmod 600 /opt/beyondtrust-password-safe-veza/.env

# Protect script directory
chmod 700 /opt/beyondtrust-password-safe-veza/

# Protect logs
chmod 700 /opt/beyondtrust-password-safe-veza/logs
chmod 640 /opt/beyondtrust-password-safe-veza/logs/*
```

### Network Security

- Run integration on a **bastion host** or dedicated VM with restricted network access
- Use **VPN or private network** to connect to BeyondTrust and Veza
- Implement **network egress controls** to only allow connections to required IPs
- Enable **TLS 1.2+** for all HTTPS connections
- Disable `--skip-ssl-verify` in production

### Audit & Monitoring

- Enable **BeyondTrust API audit logs** for all API access
- Monitor **Veza API usage** for anomalies
- Enable **Linux audit logging** (`auditd`) for `.env` access:
  ```bash
  sudo auditctl -w /opt/beyondtrust-password-safe-veza/.env -p wa -k beyondtrust-env-changes
  ```
- Set up **log aggregation** (ELK, Splunk, Datadog) for integration logs
- Implement **alerting** for integration failures or suspicious activity

---

## Troubleshooting

### Authentication Failures

**Error**: `Failed to authenticate with BeyondTrust`

**Causes & Solutions**:
1. **Incorrect credentials** — Verify API key and secret in BeyondTrust UI
   ```bash
   # Test with curl
   curl -u "YOUR_API_KEY:YOUR_API_SECRET" \
     https://api.beyondtrustcloud.com/api/v1/managed_accounts?limit=1
   ```

2. **API access not enabled** — Verify API key has proper permissions
   - Go to BeyondTrust Admin → API → API Keys
   - Check: key is "Active" and has "Read" permissions for managed_accounts and managed_computers

3. **Network blocked** — Firewall may be blocking outbound HTTPS to BeyondTrust
   ```bash
   curl -v https://api.beyondtrustcloud.com/api/v1/managed_accounts
   ```

4. **Endpoint configuration** — Custom BeyondTrust installation may use different URL
   ```bash
   # Verify API base URL
   echo $BEYONDTRUST_API_URL
   ```

### Connectivity Issues

**Error**: `API request failed: ConnectionError`

**Causes & Solutions**:
1. **Network timeout** — Increase timeout or check network path
2. **BeyondTrust API down** — Check BeyondTrust status or contact support
3. **Firewall rules** — Verify egress rules allow port 443 to BeyondTrust domain
4. **SSL certificate validation** — If legitimate, use `--skip-ssl-verify` (test only)

### CSV Parse Errors

**Error**: `Failed to parse CSV`

**Causes & Solutions**:
1. **Wrong CSV format** — Verify headers match BeyondTrust export
2. **Encoding issues** — Export CSV as UTF-8:
   ```bash
   iconv -f ISO-8859-1 -t UTF-8 input.csv > output.csv
   ```

3. **File permissions** — Check file is readable:
   ```bash
   ls -la your-file.csv
   ```

### Veza Push Failures

**Error**: `Veza push failed`

**Causes & Solutions**:
1. **Invalid API key** — Verify Veza API key is correct and active
2. **Payload too large** — Reduce number of managed computers:
   ```bash
   # Filter in script or use CSV with subset of data
   ```

3. **Network connectivity** — Test Veza connectivity:
   ```bash
   curl -H "Authorization: Bearer YOUR_VEZA_KEY" \
     https://YOUR_VEZA_INSTANCE/api/v1/applications
   ```

### Missing Data

**Issue**: Managed accounts not appearing in OAA payload

**Causes & Solutions**:
1. **CSV-only mode** — Add managed accounts API support
2. **API permissions** — Verify API key has access to managed_accounts endpoint
3. **Data filtering** — Check logs for "Fetched 0 accounts" message

**Debug steps**:
```bash
# Enable DEBUG logging
python3 beyondtrust_password_safe.py --log-level DEBUG 2>&1 | grep -A 5 "accounts\|computers"
```

### High Memory Usage

If integration consumes excessive memory with large datasets:

1. **Use CSV export** for large computer lists:
   ```bash
   python3 beyondtrust_password_safe.py \
     --csv-computers-file large-export.csv
   ```

2. **Monitor system resources**:
   ```bash
   watch -n 1 'ps aux | grep beyondtrust'
   ```

3. **Run during off-hours** — Schedule integration at low-usage times

---

## Multiple Instances

To run the integration against multiple BeyondTrust instances:

### Method 1: Separate Installation Directories

```bash
# Instance 1 (Production)
sudo mkdir -p /opt/beyondtrust-prod-veza
cd /opt/beyondtrust-prod-veza
echo "BEYONDTRUST_API_URL=https://prod-api.beyondtrustcloud.com
BEYONDTRUST_API_KEY=prod_key
BEYONDTRUST_API_SECRET=prod_secret
VEZA_URL=acme.veza.com
VEZA_API_KEY=veza_key" > .env

# Instance 2 (Development)
sudo mkdir -p /opt/beyondtrust-dev-veza
cd /opt/beyondtrust-dev-veza
echo "BEYONDTRUST_API_URL=https://dev-api.beyondtrustcloud.com
BEYONDTRUST_API_KEY=dev_key
BEYONDTRUST_API_SECRET=dev_secret
VEZA_URL=acme.veza.com
VEZA_API_KEY=veza_key" > .env
```

### Method 2: Cron Schedule Staggering

```bash
# Instance 1: 2 AM
0 2 * * * /opt/beyondtrust-prod-veza/run_integration.sh

# Instance 2: 3 AM
0 3 * * * /opt/beyondtrust-dev-veza/run_integration.sh
```

---

## Changelog

### v1.0 (2026-04-10)

- Initial release
- Read-only API integration with BeyondTrust Password Safe
- Support for managed accounts and managed computers
- CSV export parsing for offline data ingestion
- OAA payload generation and Veza push
- Automated installation script with interactive and non-interactive modes
- Comprehensive documentation and troubleshooting guide
- Cron scheduling examples and log rotation configuration
- Security best practices and credential management guidelines

---

## Support & Contributing

For issues, feature requests, or contributions, open a GitHub issue on the [OAA_Agent repository](https://github.com/pvolu-vz/OAA_Agent).

---

## License

This integration is part of the Veza OAA Agent template and is provided under the same license as the parent repository.
