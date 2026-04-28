# Panther Identity Manager to Veza OAA Integration

## Overview

This integration script collects user accounts and groups from **Panther Identity Manager** and pushes it to **Veza** via the Open Authorization API (OAA). The connector provides read-only access to:

- **User Accounts** — Employee accounts managed by Panther Identity Manager
- **Groups/Roles** — Security groups and role assignments
- **Account Attributes** — Email, employee ID, phone, full name, and active status

All data flows through Veza's OAA model, enabling centralized visibility into identity and access management (IAM) across your organization.

---

## How It Works

The integration follows this flow:

1. **Authenticate** — Validates credentials with Panther API using OAuth2 CLIENT_CREDENTIALS flow
2. **Fetch Entities** — Retrieves user accounts and groups from Panther APIs
3. **Build Payload** — Constructs a Veza CustomApplication object with:
   - Users as resources with attributes (email, employee ID, phone, etc.)
   - Groups as resources
   - IT Operations group with read-only access to all resources
4. **Push to Veza** — Sends the complete OAA payload to Veza for indexing and analysis
5. **Log Results** — Tracks metrics (resources discovered, permissions assigned, warnings)

---

## Prerequisites

### System Requirements
- **OS**: Linux (RHEL/CentOS, Ubuntu, Debian), macOS, or Windows with Python
- **Python**: 3.8 or higher
- **Internet Access**: HTTPS connectivity to Panther and Veza instances
- **Disk Space**: ≥ 500 MB (for venv and logs)

### Panther Prerequisites
- Active Panther Identity Manager instance
- OAuth2 application credentials (Client ID and Client Secret)
- Tenant ID configured in Panther
- **Required API Endpoints**: 
  - `GET /HealthCheck` (connection test)
  - `GET /v1/users` (list users)
  - `GET /v1/groups` (list groups)

### Veza Prerequisites
- Active Veza instance with API access
- Valid API key with permissions to push OAA data
- Network connectivity from integration server to Veza

### Network Requirements
- Outbound HTTPS (port 443) to Panther: `mill-mes-security.westrock.com` or configured domain
- Outbound HTTPS (port 443) to Veza instance: `*.veza.com`
- Optional: firewall rules limiting access to service account IP

---

## Quick Start

### One-Command Installation (Interactive)

```bash
curl -fsSL https://raw.githubusercontent.com/pvolu-vz/OAA_Agent/main/integrations/panther-identity-manager/install_panther.sh | bash
```

The installer will:
1. Install system dependencies (Python 3, pip, git, curl)
2. Clone the integration repository
3. Create a Python virtual environment
4. Prompt for Panther and Veza credentials
5. Generate a `.env` file with configuration
6. Create a wrapper script for cron scheduling

---

## Manual Installation

### Step 1: Clone the Repository

```bash
# Clone the OAA Agent template
git clone https://github.com/pvolu-vz/OAA_Agent.git
cd OAA_Agent/integrations/panther-identity-manager
```

### Step 2: Create Installation Directory

```bash
# Create dedicated installation directory (optional)
mkdir -p ~/panther-veza-integration
cd ~/panther-veza-integration
```

### Step 3: Set Up Python Virtual Environment

```bash
# Create venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### Step 4: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables

Create a `.env` file with your configuration:

```bash
cat > .env << EOF
# Panther Configuration
PANTHER_BASE_URL=https://mill-mes-security.westrock.com
PANTHER_CLIENT_ID=<your-client-id>
PANTHER_CLIENT_SECRET=<your-client-secret>
PANTHER_TENANT_ID=3211

# Veza Configuration
VEZA_URL=https://your-veza-instance.veza.com
VEZA_API_KEY=<your-veza-api-key>
EOF
```

**Important**: Protect the `.env` file with appropriate permissions:

```bash
chmod 600 .env
```

---

## Usage

### Test Connection

Test connectivity to Panther without pushing to Veza:

```bash
python panther.py --test --config .env
```

### Dry Run

Build the OAA payload without pushing to Veza:

```bash
python panther.py --dry-run --config .env
```

### Full Integration

Execute the complete integration pipeline:

```bash
python panther.py --config .env
```

### Custom Configuration File

```bash
python panther.py --config /path/to/config.env
```

---

## Configuration Details

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `PANTHER_BASE_URL` | Yes | Panther API base URL | `https://mill-mes-security.westrock.com` |
| `PANTHER_CLIENT_ID` | Yes | OAuth2 Client ID | `477b587c-bca6-42fd-8dab-7ced0714f571` |
| `PANTHER_CLIENT_SECRET` | Yes | OAuth2 Client Secret | (sensitive credential) |
| `PANTHER_TENANT_ID` | No | Panther tenant ID | `3211` (default) |
| `VEZA_URL` | Yes | Veza API base URL | `https://your-instance.veza.com` |
| `VEZA_API_KEY` | Yes | Veza API key | (sensitive credential) |

### Panther OAuth2 Configuration

The integration uses OAuth2 CLIENT_CREDENTIALS flow with:
- **Token URL**: `https://login.microsoftonline.com/WestRockCo.onmicrosoft.com/oauth2/v2.0/token`
- **Scope**: `api://mill-mes-api/.default`
- **Grant Type**: `client_credentials`

---

## Data Mapping

### User Attributes

Panther user fields mapped to Veza resource properties:

| Panther Field | Veza Property | Type |
|---------------|---------------|------|
| `userName` | Name | String |
| `email` | Email | String |
| `fullName` | Full Name | String |
| `employeeId` | Employee ID | String |
| `phoneNumber` | Phone Number | String |
| `isActive` | Is Active | String |

### Group Attributes

| Panther Field | Veza Property | Type |
|---------------|---------------|------|
| `groupName` | Name | String |

### Permissions Model

- **IT Operations** group is created with `Read` permissions on all user and group resources
- All other subjects inherit permissions based on Panther group assignments

---

## Scheduling

### Linux/macOS - Cron

Schedule the integration to run daily at 2 AM:

```bash
# Add to crontab
crontab -e

# Add entry
0 2 * * * cd ~/panther-veza-integration && source venv/bin/activate && python panther.py --config .env >> logs/cron.log 2>&1
```

### Windows - Task Scheduler

Create a scheduled task:

```powershell
# PowerShell (Run as Administrator)
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "panther.py --config .env" -WorkingDirectory "C:\panther-veza-integration"
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "Panther-Veza-Integration" -Description "Daily Panther to Veza integration"
```

---

## Troubleshooting

### Authentication Failed

**Error**: "Authentication failed: 401 Unauthorized"

**Solutions**:
- Verify `PANTHER_CLIENT_ID` and `PANTHER_CLIENT_SECRET` are correct
- Confirm OAuth2 application is active in Panther
- Check token URL is accessible: `https://login.microsoftonline.com/...`
- Verify tenant ID is correct

### Health Check Failed

**Error**: "Health check failed: 404 Not Found"

**Solutions**:
- Verify `PANTHER_BASE_URL` is correct and accessible
- Check network connectivity to Panther
- Confirm `/HealthCheck` endpoint is available
- Verify Panther instance is running

### No Users Retrieved

**Error**: "Retrieved 0 users from Panther"

**Solutions**:
- Check users exist in Panther system
- Verify OAuth2 credentials have read permission
- Confirm `/v1/users` endpoint is available
- Check Panther API is responding correctly

### Veza Connection Failed

**Error**: "Failed to push to Veza"

**Solutions**:
- Verify `VEZA_URL` and `VEZA_API_KEY` are correct
- Check network connectivity to Veza
- Confirm API key has OAA push permissions
- Review Veza API documentation for payload requirements

---

## Log Files

Logs are written to:
- **Console**: Real-time output for monitoring
- **File**: `panther_veza_integration.log` - Detailed execution logs

View logs:

```bash
tail -f panther_veza_integration.log
```

---

## Performance Considerations

- **User Limit**: Each integration run processes all users; typical load: ~100-5000 users
- **API Rate Limiting**: Panther may enforce rate limits; adjust timeout in script if needed
- **Memory Usage**: Typical usage: 100-200 MB for 5000+ users
- **Network Bandwidth**: Data transfer depends on group assignments and attributes

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review log files for detailed error messages
3. Contact Veza support: `support@veza.com`
4. Contact Panther support or system administrator

---

## Version History

- **1.0.0** (2026-04-23) - Initial release
  - User account aggregation
  - Group aggregation
  - Basic RBAC model for IT Operations

---

## License

This integration is part of the Veza OAA Agent project. See LICENSE file for details.
