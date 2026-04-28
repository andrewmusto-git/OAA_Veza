# Palantir Foundry to Veza OAA Integration

## Overview

This integration script collects data governance and access control information from **Palantir Foundry** and pushes it to **Veza** via the Open Authorization API (OAA). The connector provides read-only visibility into:

- **Workspaces** — Logical groupings for collaborative work and projects
- **Projects** — Organizational units within workspaces
- **Datasets** — Data assets and their metadata
- **Access Controls** — Fine-grained permissions and role assignments

All data flows through Veza's OAA model, enabling centralized visibility into data governance, lineage, and access management across your Palantir Foundry deployment.

---

## How It Works

The integration follows this flow:

1. **Authenticate** — Validates credentials with Palantir Foundry API using bearer token
2. **Fetch Resources** — Retrieves workspaces, projects, and datasets from Foundry APIs
3. **Build Payload** — Constructs a Veza CustomApplication object with:
   - Workspaces as container resources
   - Projects as organizational resources
   - Datasets as data assets with metadata
   - Access control information and permissions
4. **Push to Veza** — Sends the complete OAA payload to Veza for indexing and analysis
5. **Log Results** — Tracks metrics (resources discovered, permissions mapped, warnings)

---

## Prerequisites

### System Requirements
- **OS**: Linux (RHEL/CentOS, Ubuntu, Debian), macOS, or Windows with Python
- **Python**: 3.8 or higher
- **Internet Access**: HTTPS connectivity to Palantir Foundry and Veza instances
- **Disk Space**: ≥ 500 MB (for venv and logs)

### Palantir Foundry Prerequisites
- Active Palantir Foundry instance at `https://westrock.palantirfoundry.com/`
- API token with read access to resources
- **Required API Endpoints**: 
  - `GET /api/foundry/core/v1/user` (authentication)
  - `GET /api/foundry/core/v1/healthcheck` (health check)
  - `GET /api/foundry/datasets/v1/datasets` (list datasets)
  - `GET /api/foundry/projects/v1/projects` (list projects)
  - `GET /api/foundry/workspaces/v1/workspaces` (list workspaces)

### Veza Prerequisites
- Active Veza instance with API access
- Valid API key with permissions to push OAA data
- Network connectivity from integration server to Veza

### Network Requirements
- Outbound HTTPS (port 443) to Palantir Foundry: `westrock.palantirfoundry.com`
- Outbound HTTPS (port 443) to Veza instance: `*.veza.com`
- Optional: firewall rules limiting access to service account IP

---

## Quick Start

### One-Command Installation (Interactive)

```bash
curl -fsSL https://raw.githubusercontent.com/andrewmusto-git/OAA_Agent-1/main/integrations/palantir-foundry/install_palantir_foundry.sh | bash
```

The installer will:
1. Install system dependencies (Python 3, pip, git, curl)
2. Clone the integration repository
3. Create a Python virtual environment
4. Prompt for Palantir Foundry and Veza credentials
5. Generate a `.env` file with configuration
6. Create a wrapper script for cron scheduling

---

## Manual Installation

### Step 1: Clone the Repository

```bash
# Clone the OAA Agent template
git clone https://github.com/andrewmusto-git/OAA_Agent-1.git
cd OAA_Agent/integrations/palantir-foundry
```

### Step 2: Create Installation Directory

```bash
# Create dedicated installation directory (optional)
mkdir -p ~/palantir-foundry-veza
cd ~/palantir-foundry-veza
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
# Palantir Foundry Configuration
FOUNDRY_BASE_URL=https://westrock.palantirfoundry.com/
FOUNDRY_API_TOKEN=<your-api-token>

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

Test connectivity to Palantir Foundry without pushing to Veza:

```bash
python palantir_foundry.py --test --config .env
```

### Dry Run

Build the OAA payload without pushing to Veza:

```bash
python palantir_foundry.py --dry-run --config .env
```

### Full Integration

Execute the complete integration pipeline:

```bash
python palantir_foundry.py --config .env
```

### Custom Configuration File

```bash
python palantir_foundry.py --config /path/to/config.env
```

---

## Configuration Details

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `FOUNDRY_BASE_URL` | Yes | Palantir Foundry base URL | `https://westrock.palantirfoundry.com/` |
| `FOUNDRY_API_TOKEN` | Yes | API token for authentication | (sensitive credential) |
| `VEZA_URL` | Yes | Veza API base URL | `https://your-instance.veza.com` |
| `VEZA_API_KEY` | Yes | Veza API key | (sensitive credential) |

### Palantir Foundry API Configuration

The integration uses bearer token authentication with:
- **Base URL**: `https://westrock.palantirfoundry.com/`
- **Authentication Method**: Bearer token in Authorization header
- **Content-Type**: `application/json`

---

## Data Mapping

### Workspace Attributes

Palantir Foundry workspace fields mapped to Veza resource properties:

| Foundry Field | Veza Property | Type |
|---------------|---------------|------|
| `id` | Name | String |
| `name` | Display Name | String |
| `description` | Description | String |
| `createdDate` | Created | String |

### Project Attributes

| Foundry Field | Veza Property | Type |
|---------------|---------------|------|
| `id` | Name | String |
| `name` | Display Name | String |
| `description` | Description | String |
| `workspaceId` | Workspace | String |
| `createdDate` | Created | String |

### Dataset Attributes

| Foundry Field | Veza Property | Type |
|---------------|---------------|------|
| `id` | Name | String |
| `name` | Display Name | String |
| `description` | Description | String |
| `createdDate` | Created | String |
| `modifiedDate` | Modified | String |
| `ownerId` | Owner ID | String |
| `type` | Type | String |

---

## Scheduling

### Linux/macOS - Cron

Schedule the integration to run daily at 3 AM:

```bash
# Add to crontab
crontab -e

# Add entry
0 3 * * * cd ~/palantir-foundry-veza && source venv/bin/activate && python palantir_foundry.py --config .env >> logs/cron.log 2>&1
```

### Windows - Task Scheduler

Create a scheduled task:

```powershell
# PowerShell (Run as Administrator)
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "palantir_foundry.py --config .env" -WorkingDirectory "C:\palantir-foundry-veza"
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "Palantir-Foundry-Veza-Integration" -Description "Daily Palantir Foundry to Veza integration"
```

---

## Troubleshooting

### Authentication Failed

**Error**: "Authentication failed: 401 Unauthorized"

**Solutions**:
- Verify `FOUNDRY_API_TOKEN` is correct and not expired
- Confirm API token has necessary read permissions
- Check token is not revoked in Palantir Foundry admin console
- Verify base URL is correct: `https://westrock.palantirfoundry.com/`

### Health Check Failed

**Error**: "Health check failed: 404 Not Found"

**Solutions**:
- Verify `FOUNDRY_BASE_URL` is correct and accessible
- Check network connectivity to Palantir Foundry
- Confirm `/api/foundry/core/v1/healthcheck` endpoint is available
- Verify Palantir Foundry instance is running and responsive

### No Resources Retrieved

**Error**: "No datasets, projects, or workspaces retrieved"

**Solutions**:
- Check resources exist in Palantir Foundry
- Verify API token has read permission on resources
- Confirm `/api/foundry/*/v1/*` endpoints are available
- Check Palantir Foundry API is responding correctly
- Review Palantir Foundry logs for access issues

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
- **File**: `palantir_foundry_veza_integration.log` - Detailed execution logs

View logs:

```bash
tail -f palantir_foundry_veza_integration.log
```

---

## Performance Considerations

- **Resource Limit**: Each integration run processes all resources; typical load: 100-10,000+ datasets
- **API Rate Limiting**: Palantir Foundry may enforce rate limits; adjust timeout if needed
- **Memory Usage**: Typical usage: 100-500 MB depending on resource count
- **Network Bandwidth**: Data transfer depends on metadata size and number of resources
- **Pagination**: API implements pagination; script handles automatically

---

## Advanced Features

### Custom Filtering

To limit integration to specific resources, modify the `build_payload()` method:

```python
# Filter datasets by type
datasets = [d for d in datasets if d.get('type') == 'SQL']

# Filter projects by name pattern
projects = [p for p in projects if 'production' in p.get('name', '').lower()]
```

### Access Control Analysis

To include detailed access control information:

```python
# Add to build_payload() after creating resources
for dataset in datasets:
    dataset_id = dataset.get('id')
    access_controls = self.foundry.get_access_controls(dataset_id, 'dataset')
    # Process access controls and create subjects/permissions
```

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review log files for detailed error messages
3. Contact Veza support: `support@veza.com`
4. Contact Palantir support: `support@palantir.com`

---

## Version History

- **1.0.0** (2026-04-27) - Initial release
  - Workspace aggregation
  - Project aggregation
  - Dataset discovery with metadata
  - Basic resource mapping to Veza OAA model

---

## License

This integration is part of the Veza OAA Agent project. See LICENSE file for details.
