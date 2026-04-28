# SailPoint Identity Security Cloud to Veza OAA Integration

## Overview

This integration script collects identity and permission data from **SailPoint Identity Security Cloud** and pushes it to **Veza** via the Open Authorization API (OAA). The connector provides read-only access to:

- **Identities** — Users within the SailPoint instance
- **Roles** — Role definitions and role assignments
- **Access Profiles** — Access profile definitions and memberships
- **Entitlements** — Entitlements from configured sources
- **Sources** — HR, directory, and application sources connected to SailPoint

All data flows through Veza's OAA model, enabling centralized visibility into identity and access governance across your organization.

---

## How It Works

The integration follows this flow:

1. **Authenticate** — Obtains an OAuth2 access token from SailPoint using client credentials
2. **Fetch Entities** — Retrieves identities, roles, access profiles, entitlements, and sources from SailPoint APIs
3. **Build Payload** — Constructs a Veza CustomApplication object with:
   - Local users (identities)
   - Resources (roles, access profiles, entitlements, sources)
   - Permission assignments (user → resource)
4. **Push to Veza** — Sends the complete OAA payload to Veza for indexing and analysis
5. **Log Results** — Tracks metrics (entities discovered, assignments created, warnings)

---

## Prerequisites

### System Requirements
- **OS**: Linux (RHEL/CentOS, Ubuntu, Debian) or macOS
- **Python**: 3.8 or higher
- **Internet Access**: HTTPS connectivity to SailPoint and Veza instances
- **Disk Space**: ≥ 500 MB (for venv and logs)

### SailPoint Prerequisites
- Active SailPoint Identity Security Cloud tenant
- OAuth2 application configured in SailPoint with client credentials flow
- **Required Scopes**: `roles:read`, `sources:read`, `access-profiles:read`, `entitlements:read`, `identities:read`

### Veza Prerequisites
- Active Veza instance with API access
- Valid API key with permissions to push OAA data
- Network connectivity from integration server to Veza

### Network Requirements
- Outbound HTTPS (port 443) to SailPoint tenant: `*.identitynow.com`
- Outbound HTTPS (port 443) to Veza instance: `*.veza.com`

---

## Quick Start

### One-Command Installation (Interactive)

```bash
curl -fsSL https://raw.githubusercontent.com/pvolu-vz/OAA_Agent/main/integrations/sailpoint-identity-security-cloud/install_sailpoint_identity_security_cloud.sh | bash
```

The installer will:
1. Install system dependencies (Python 3, pip, git, curl)
2. Clone the integration repository
3. Create a Python virtual environment
4. Prompt for SailPoint and Veza credentials
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
sudo mkdir -p /opt/sailpoint-identity-security-cloud-veza
sudo chown $USER:$USER /opt/sailpoint-identity-security-cloud-veza
cd /opt/sailpoint-identity-security-cloud-veza
```

### Step 3: Set Up Python Virtual Environment

```bash
# Create venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r integrations/sailpoint-identity-security-cloud/requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy the example .env
cp integrations/sailpoint-identity-security-cloud/.env.example .env

# Edit .env with your credentials
nano .env
```

### Step 5: Test the Integration

```bash
# Dry-run (don't push to Veza)
python3 integrations/sailpoint-identity-security-cloud/sailpoint_identity_security_cloud.py --dry-run

# Live push
python3 integrations/sailpoint-identity-security-cloud/sailpoint_identity_security_cloud.py
```

---

## Usage

### CLI Arguments

```
python3 sailpoint_identity_security_cloud.py [OPTIONS]

OPTIONS:
  --sailpoint-tenant-url TEXT      SailPoint tenant URL [required]
                                   Env: SAILPOINT_TENANT_URL
                                   Format: https://acme.identitynow.com

  --sailpoint-client-id TEXT       OAuth2 client ID [required]
                                   Env: SAILPOINT_CLIENT_ID

  --sailpoint-client-secret TEXT   OAuth2 client secret [required]
                                   Env: SAILPOINT_CLIENT_SECRET

  --veza-url TEXT                  Veza instance URL [required]
                                   Env: VEZA_URL
                                   Format: acme.veza.com or https://acme.veza.com

  --veza-api-key TEXT              Veza API key [required]
                                   Env: VEZA_API_KEY

  --provider-name TEXT             Veza provider name
                                   Default: SailPoint Identity Security Cloud
                                   Env: PROVIDER_NAME

  --datasource-name TEXT           Veza data source name
                                   Default: <tenant-subdomain> (e.g., "acme")
                                   Env: DATASOURCE_NAME

  --env-file PATH                  Path to .env file
                                   Default: .env

  --dry-run                        Build payload but skip push to Veza

  --log-level {DEBUG,INFO,WARNING,ERROR}
                                   Logging level
                                   Default: INFO

  --help                           Show help message
```

### Examples

#### Example 1: Basic Usage with Environment File

```bash
python3 sailpoint_identity_security_cloud.py
```

Reads credentials from `.env` in current directory.

#### Example 2: Dry-Run Test

```bash
python3 sailpoint_identity_security_cloud.py --dry-run --log-level DEBUG
```

Tests authentication and data collection without pushing to Veza.

#### Example 3: Custom Names

```bash
python3 sailpoint_identity_security_cloud.py \
  --provider-name "ACME SailPoint" \
  --datasource-name "ACME Production"
```

#### Example 4: Non-Interactive (CI/CD)

```bash
SAILPOINT_TENANT_URL=https://acme.identitynow.com \
SAILPOINT_CLIENT_ID=client123 \
SAILPOINT_CLIENT_SECRET=secret456 \
VEZA_URL=acme.veza.com \
VEZA_API_KEY=veza_key_789 \
python3 sailpoint_identity_security_cloud.py
```

---

## Deployment on Linux

### Create Service Account

```bash
# Create dedicated service account
sudo useradd -r -s /bin/bash -m -d /opt/sailpoint-identity-security-cloud-veza sailpoint-veza

# Set permissions
sudo chown -R sailpoint-veza:sailpoint-veza /opt/sailpoint-identity-security-cloud-veza
sudo chmod 700 /opt/sailpoint-identity-security-cloud-veza
sudo chmod 600 /opt/sailpoint-identity-security-cloud-veza/.env
```

### Schedule with Cron

#### Example 1: Daily at 2 AM

```bash
# Edit crontab
sudo crontab -e -u sailpoint-veza

# Add line:
0 2 * * * bash /opt/sailpoint-identity-security-cloud-veza/run_integration.sh >> /opt/sailpoint-identity-security-cloud-veza/logs/cron.log 2>&1
```

#### Example 2: Every 6 Hours

```bash
0 */6 * * * bash /opt/sailpoint-identity-security-cloud-veza/run_integration.sh >> /opt/sailpoint-identity-security-cloud-veza/logs/cron.log 2>&1
```

#### Example 3: Every Hour on Weekdays

```bash
0 * * * 1-5 bash /opt/sailpoint-identity-security-cloud-veza/run_integration.sh >> /opt/sailpoint-identity-security-cloud-veza/logs/cron.log 2>&1
```

### Configure Log Rotation (RHEL/CentOS)

```bash
# Create logrotate config
sudo tee /etc/logrotate.d/sailpoint-veza > /dev/null << 'EOF'
/opt/sailpoint-identity-security-cloud-veza/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 sailpoint-veza sailpoint-veza
    sharedscripts
}
EOF

# Test logrotate
sudo logrotate -vf /etc/logrotate.d/sailpoint-veza
```

### Configure Log Rotation (Ubuntu/Debian)

```bash
# Create logrotate config
sudo tee /etc/logrotate.d/sailpoint-veza > /dev/null << 'EOF'
/opt/sailpoint-identity-security-cloud-veza/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 sailpoint-veza sailpoint-veza
}
EOF
```

### SELinux Configuration (RHEL/CentOS)

If you see permission errors related to SELinux:

```bash
# Check SELinux status
getenforce

# If enforcing, allow venv access
sudo chcon -Rv -t user_home_t /opt/sailpoint-identity-security-cloud-veza/

# Verify
ls -Z /opt/sailpoint-identity-security-cloud-veza/
```

---

## Multiple Instances

To run the integration against multiple SailPoint tenants:

### Method 1: Separate Installation Directories

```bash
# Instance 1 (Production)
sudo mkdir -p /opt/sailpoint-prod-veza
cd /opt/sailpoint-prod-veza
cp /path/to/sailpoint_identity_security_cloud.py .
cp /path/to/requirements.txt .
echo "SAILPOINT_TENANT_URL=https://prod.identitynow.com
SAILPOINT_CLIENT_ID=prod_client
SAILPOINT_CLIENT_SECRET=prod_secret
VEZA_URL=acme.veza.com
VEZA_API_KEY=veza_key" > .env

# Instance 2 (Development)
sudo mkdir -p /opt/sailpoint-dev-veza
cd /opt/sailpoint-dev-veza
cp /path/to/sailpoint_identity_security_cloud.py .
cp /path/to/requirements.txt .
echo "SAILPOINT_TENANT_URL=https://dev.identitynow.com
SAILPOINT_CLIENT_ID=dev_client
SAILPOINT_CLIENT_SECRET=dev_secret
VEZA_URL=acme.veza.com
VEZA_API_KEY=veza_key" > .env
```

### Method 2: Single Installation with Separate .env Files

```bash
# Base installation
/opt/sailpoint-identity-security-cloud-veza/
├── sailpoint_identity_security_cloud.py
├── venv/
├── .env.prod
├── .env.dev

# Cron entries
0 2 * * * bash /opt/sailpoint-identity-security-cloud-veza/run_integration.sh --env-file .env.prod
0 3 * * * bash /opt/sailpoint-identity-security-cloud-veza/run_integration.sh --env-file .env.dev
```

### Stagger Cron Schedules

To avoid concurrent runs, stagger execution times:

```bash
# Tenant 1: 2 AM
0 2 * * * /opt/sailpoint-prod-veza/run_integration.sh

# Tenant 2: 3 AM
0 3 * * * /opt/sailpoint-dev-veza/run_integration.sh

# Tenant 3: 4 AM
0 4 * * * /opt/sailpoint-staging-veza/run_integration.sh
```

---

## Security Considerations

### Credential Management

- **Never commit `.env` files to Git** — add to `.gitignore`
- **Rotate API keys regularly** — SailPoint and Veza keys should be rotated quarterly
- **Use a secrets manager** (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) in production
- **Implement least privilege** — SailPoint OAuth app should only have required scopes

### File Permissions

```bash
# Protect .env file
chmod 600 /opt/sailpoint-identity-security-cloud-veza/.env

# Protect script directory
chmod 700 /opt/sailpoint-identity-security-cloud-veza/

# Protect logs
chmod 700 /opt/sailpoint-identity-security-cloud-veza/logs
chmod 640 /opt/sailpoint-identity-security-cloud-veza/logs/*
```

### Network Security

- Run integration on a **bastion host** or dedicated VM with restricted network access
- Use **VPN or private network** to connect to SailPoint and Veza
- Implement **network egress controls** to only allow connections to required SailPoint/Veza IPs
- Enable **TLS 1.2+** for all HTTPS connections

### Audit & Monitoring

- Enable **SailPoint API audit logs** for OAuth app activity
- Monitor **Veza API usage** for anomalies
- Enable **Linux audit logging** (`auditd`) for `.env` access:
  ```bash
  sudo auditctl -w /opt/sailpoint-identity-security-cloud-veza/.env -p wa -k sailpoint-env-changes
  ```
- Set up **log aggregation** (ELK, Splunk, Datadog) for integration logs

---

## Troubleshooting

### Authentication Failures

**Error**: `Failed to authenticate with SailPoint`

**Causes & Solutions**:
1. **Incorrect credentials** — Verify client ID and secret in SailPoint UI
   ```bash
   # Test with curl
   curl -X POST https://acme.identitynow.com/oauth/token \
     -d "grant_type=client_credentials&client_id=YOUR_ID&client_secret=YOUR_SECRET"
   ```

2. **Client not authorized** — Verify OAuth app is enabled and has required scopes
   - Go to SailPoint Admin → System Configuration → OAuth Applications
   - Check: client is "Active" and has scopes: `roles:read`, `sources:read`, `access-profiles:read`, `entitlements:read`, `identities:read`

3. **Network blocked** — Firewall may be blocking outbound HTTPS to SailPoint
   ```bash
   curl -v https://acme.identitynow.com/oauth/token
   ```

### Connectivity Issues

**Error**: `API request failed: ConnectionError`

**Causes & Solutions**:
1. **Network timeout** — Increase timeout or check network path
2. **SailPoint API down** — Check SailPoint status page
3. **Firewall rules** — Verify egress rules allow port 443 to `*.identitynow.com`

### Permission Denied Errors

**Error**: `Permission denied: .env` or `Permission denied: logs`

**Solution**:
```bash
sudo chown -R sailpoint-veza:sailpoint-veza /opt/sailpoint-identity-security-cloud-veza
chmod 700 /opt/sailpoint-identity-security-cloud-veza
chmod 600 /opt/sailpoint-identity-security-cloud-veza/.env
chmod 700 /opt/sailpoint-identity-security-cloud-veza/logs
```

### Missing Python Modules

**Error**: `ModuleNotFoundError: No module named 'oaaclient'`

**Solution**:
```bash
source /opt/sailpoint-identity-security-cloud-veza/venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Veza Push Warnings

Check Veza logs for specific validation issues. Common warnings:
- **Circular permissions** — User has both `read` and `admin` permissions on same resource
- **Missing attributes** — Required OAA attributes missing on entities
- **Duplicate resource IDs** — Two resources share the same ID

**Solution**: Check raw payload with `--dry-run`:
```bash
python3 sailpoint_identity_security_cloud.py --dry-run --log-level DEBUG 2>&1 | grep -A 5 "warning"
```

### High Memory Usage

If integration is consuming excessive memory with large SailPoint instances:

1. **Reduce batch size** — API pagination defaults to 250 items; adjust if needed
2. **Run during off-hours** — Schedule integration at low-usage times
3. **Monitor system resources**:
   ```bash
   watch -n 1 'ps aux | grep sailpoint'
   ```

---

## Changelog

### v1.0 (2026-04-10)

- Initial release
- Read-only API integration with SailPoint Identity Security Cloud
- Support for identities, roles, access profiles, entitlements, and sources
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
