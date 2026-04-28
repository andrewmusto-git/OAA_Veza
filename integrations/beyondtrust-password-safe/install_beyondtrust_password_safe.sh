#!/usr/bin/env bash
# install_beyondtrust_password_safe.sh — One-command installer for BeyondTrust Password Safe-Veza OAA integration
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SYSTEM_NAME="beyondtrust-password-safe"
INSTALL_DIR="/opt/${SYSTEM_NAME}-veza"
SCRIPT_DIR="${INSTALL_DIR}/scripts"
LOGS_DIR="${INSTALL_DIR}/logs"
REPO_URL="${REPO_URL:-https://github.com/pvolu-vz/OAA_Agent.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
INTERACTIVE=true
OVERWRITE_ENV=false

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

print_header() {
    echo ""
    echo "================================================================================================"
    echo "$*"
    echo "================================================================================================"
    echo ""
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

OPTIONS:
    --non-interactive           Enable non-interactive mode (requires env vars)
    --overwrite-env             Overwrite existing .env file
    --install-dir <path>        Custom installation directory (default: ${INSTALL_DIR})
    --repo-url <url>            Custom repository URL (default: ${REPO_URL})
    --branch <name>             Repository branch to clone (default: ${REPO_BRANCH})
    --help                      Show this help message

ENVIRONMENT VARIABLES (non-interactive mode):
    BEYONDTRUST_API_URL         BeyondTrust API base URL
    BEYONDTRUST_API_KEY         BeyondTrust API key
    BEYONDTRUST_API_SECRET      BeyondTrust API secret
    VEZA_URL                    Veza instance URL
    VEZA_API_KEY                Veza API key

EXAMPLES:
    # Interactive installation
    bash install_beyondtrust_password_safe.sh

    # Non-interactive installation
    BEYONDTRUST_API_URL=https://api.beyondtrustcloud.com \\
    BEYONDTRUST_API_KEY=api_key_123 \\
    BEYONDTRUST_API_SECRET=api_secret_456 \\
    VEZA_URL=acme.veza.com \\
    VEZA_API_KEY=veza_key_789 \\
    bash install_beyondtrust_password_safe.sh --non-interactive

EOF
}

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif [ -f /etc/redhat-release ]; then
        echo "rhel"
    elif [ -f /etc/debian_version ]; then
        echo "debian"
    else
        echo "unknown"
    fi
}

install_system_dependencies() {
    local distro=$(detect_distro)
    
    print_header "Installing System Dependencies"
    
    if [[ "$distro" =~ ^(rhel|centos|fedora)$ ]]; then
        print_info "Detected RHEL/CentOS/Fedora-based system"
        if command -v dnf &> /dev/null; then
            print_info "Using dnf package manager"
            sudo dnf install -y git curl python3 python3-pip python3-venv || return 1
        else
            print_info "Using yum package manager"
            sudo yum install -y git curl python3 python3-pip || return 1
        fi
    elif [[ "$distro" =~ ^(debian|ubuntu)$ ]]; then
        print_info "Detected Debian/Ubuntu-based system"
        sudo apt-get update || true
        sudo apt-get install -y git curl python3 python3-pip python3-venv || return 1
    else
        print_warn "Unknown Linux distribution: $distro — assuming git, curl, python3, python3-pip are installed"
    fi
}

check_python_version() {
    print_header "Checking Python Version"
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        return 1
    fi
    
    local python_version=$(python3 --version 2>&1 | awk '{print $2}')
    local major=$(echo "$python_version" | cut -d. -f1)
    local minor=$(echo "$python_version" | cut -d. -f2)
    
    print_info "Found Python ${python_version}"
    
    if [[ $major -lt 3 ]] || [[ $major -eq 3 && $minor -lt 8 ]]; then
        print_error "Python 3.8+ is required (found $python_version)"
        return 1
    fi
    
    print_info "Python version OK"
}

clone_or_update_repo() {
    print_header "Cloning/Updating Repository"
    
    if [ -d "$SCRIPT_DIR/.git" ]; then
        print_info "Repository already exists at $SCRIPT_DIR — updating..."
        cd "$SCRIPT_DIR"
        git fetch origin
        git checkout "$REPO_BRANCH"
        git pull origin "$REPO_BRANCH" || print_warn "Could not pull latest changes"
    else
        print_info "Cloning repository from $REPO_URL (branch: $REPO_BRANCH)"
        mkdir -p "$SCRIPT_DIR"
        git clone --branch "$REPO_BRANCH" "$REPO_URL" "$SCRIPT_DIR" || return 1
    fi
    
    # Copy integration files to install directory
    if [ -f "$SCRIPT_DIR/integrations/${SYSTEM_NAME}/beyondtrust_password_safe.py" ]; then
        cp "$SCRIPT_DIR/integrations/${SYSTEM_NAME}/beyondtrust_password_safe.py" "$INSTALL_DIR/"
        cp "$SCRIPT_DIR/integrations/${SYSTEM_NAME}/requirements.txt" "$INSTALL_DIR/"
        print_info "Copied integration files to $INSTALL_DIR"
    else
        print_warn "Integration files not found in cloned repo"
    fi
}

create_venv() {
    print_header "Creating Python Virtual Environment"
    
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        print_info "Creating venv at $INSTALL_DIR/venv"
        python3 -m venv "$INSTALL_DIR/venv" || return 1
    else
        print_info "Virtual environment already exists"
    fi
    
    # Activate and upgrade pip
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --upgrade pip setuptools wheel
    
    # Install requirements
    print_info "Installing Python dependencies..."
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        pip install -r "$INSTALL_DIR/requirements.txt" || return 1
    else
        print_warn "requirements.txt not found — installing base dependencies"
        pip install oaaclient python-dotenv requests urllib3
    fi
    
    deactivate
}

interactive_credentials() {
    print_header "BeyondTrust Credentials"
    
    echo "Please provide your BeyondTrust API credentials:"
    echo ""
    
    read -p "BeyondTrust API Base URL (e.g., https://api.beyondtrustcloud.com): " BEYONDTRUST_API_URL
    read -p "BeyondTrust API Key: " BEYONDTRUST_API_KEY
    read -sp "BeyondTrust API Secret: " BEYONDTRUST_API_SECRET
    echo ""
    
    print_header "Veza Credentials"
    
    echo "Please provide your Veza API credentials:"
    echo ""
    
    read -p "Veza Instance URL (e.g., acme.veza.com): " VEZA_URL
    read -sp "Veza API Key: " VEZA_API_KEY
    echo ""
}

validate_credentials() {
    if [ -z "${BEYONDTRUST_API_URL:-}" ] || [ -z "${BEYONDTRUST_API_KEY:-}" ] || [ -z "${BEYONDTRUST_API_SECRET:-}" ]; then
        print_error "Missing BeyondTrust credentials"
        return 1
    fi
    
    if [ -z "${VEZA_URL:-}" ] || [ -z "${VEZA_API_KEY:-}" ]; then
        print_error "Missing Veza credentials"
        return 1
    fi
    
    print_info "All credentials provided"
}

create_env_file() {
    print_header "Generating .env File"
    
    local env_file="$INSTALL_DIR/.env"
    
    if [ -f "$env_file" ] && [ "$OVERWRITE_ENV" != "true" ]; then
        print_warn ".env file already exists — skipping generation"
        print_info "Use --overwrite-env to replace existing .env file"
        return 0
    fi
    
    cat > "$env_file" << EOF
# BeyondTrust Password Safe Source Configuration
BEYONDTRUST_API_URL=${BEYONDTRUST_API_URL}
BEYONDTRUST_API_KEY=${BEYONDTRUST_API_KEY}
BEYONDTRUST_API_SECRET=${BEYONDTRUST_API_SECRET}

# Veza Configuration
VEZA_URL=${VEZA_URL}
VEZA_API_KEY=${VEZA_API_KEY}

# Optional OAA Provider Settings
# PROVIDER_NAME=BeyondTrust Password Safe
# DATASOURCE_NAME=BeyondTrust Instance

# Optional Settings
# SKIP_SSL_VERIFY=false
EOF

    chmod 600 "$env_file"
    print_info "Generated $env_file (chmod 600)"
}

create_service_account() {
    print_header "Creating Service Account (Optional)"
    
    print_info "Attempting to create dedicated service account..."
    
    if id "${SYSTEM_NAME}-veza" &>/dev/null 2>&1; then
        print_warn "Service account '${SYSTEM_NAME}-veza' already exists"
    else
        if sudo useradd -r -s /bin/bash -m -d "$INSTALL_DIR" "${SYSTEM_NAME}-veza" 2>/dev/null; then
            print_info "Created service account: ${SYSTEM_NAME}-veza"
            sudo chown -R "${SYSTEM_NAME}-veza:${SYSTEM_NAME}-veza" "$INSTALL_DIR"
            print_info "Set ownership: $INSTALL_DIR"
        else
            print_warn "Could not create service account (requires sudo)"
            print_warn "Manual service account creation may be needed"
        fi
    fi
}

create_wrapper_script() {
    print_header "Creating Wrapper Script for Cron"
    
    local wrapper_script="$INSTALL_DIR/run_integration.sh"
    
    cat > "$wrapper_script" << 'EOF'
#!/usr/bin/env bash
# Wrapper script for running BeyondTrust integration via cron
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/beyondtrust-integration-$(date +%Y%m%d-%H%M%S).log"

# Activate virtual environment and run integration
source "$SCRIPT_DIR/venv/bin/activate"
"$SCRIPT_DIR/venv/bin/python3" "$SCRIPT_DIR/beyondtrust_password_safe.py" \
    --env-file "$SCRIPT_DIR/.env" \
    --log-level INFO \
    >> "$LOG_FILE" 2>&1

echo "Integration completed. Log: $LOG_FILE"
EOF

    chmod 755 "$wrapper_script"
    print_info "Created wrapper script: $wrapper_script"
}

print_summary() {
    print_header "Installation Summary"
    
    cat << EOF
✓ Installation completed successfully!

Location:       $INSTALL_DIR
Scripts:        $SCRIPT_DIR
Logs:           $LOGS_DIR
Config:         $INSTALL_DIR/.env
Wrapper:        $INSTALL_DIR/run_integration.sh

NEXT STEPS:

1. Test the integration:
   bash $INSTALL_DIR/run_integration.sh --dry-run

2. Schedule with cron (example: daily at 2 AM):
   0 2 * * * bash $INSTALL_DIR/run_integration.sh >> $LOGS_DIR/cron.log 2>&1

3. View logs:
   tail -f $LOGS_DIR/*.log

4. View usage documentation:
   cat $INSTALL_DIR/README.md

For detailed configuration and troubleshooting, see:
   $INSTALL_DIR/README.md

EOF
}

# Main installation flow
main() {
    print_header "BeyondTrust Password Safe-Veza OAA Integration Installer"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --non-interactive)
                INTERACTIVE=false
                shift
                ;;
            --overwrite-env)
                OVERWRITE_ENV=true
                shift
                ;;
            --install-dir)
                INSTALL_DIR="$2"
                SCRIPT_DIR="${INSTALL_DIR}/scripts"
                LOGS_DIR="${INSTALL_DIR}/logs"
                shift 2
                ;;
            --repo-url)
                REPO_URL="$2"
                shift 2
                ;;
            --branch)
                REPO_BRANCH="$2"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Create installation directories
    mkdir -p "$INSTALL_DIR" "$SCRIPT_DIR" "$LOGS_DIR"
    
    # Install system dependencies
    install_system_dependencies || {
        print_error "Failed to install system dependencies"
        exit 1
    }
    
    # Check Python version
    check_python_version || {
        print_error "Python version check failed"
        exit 1
    }
    
    # Clone or update repository
    clone_or_update_repo || {
        print_error "Failed to clone/update repository"
        exit 1
    }
    
    # Create virtual environment
    create_venv || {
        print_error "Failed to create virtual environment"
        exit 1
    }
    
    # Get credentials
    if [ "$INTERACTIVE" = true ]; then
        interactive_credentials
    fi
    
    validate_credentials || {
        print_error "Credential validation failed"
        exit 1
    }
    
    # Create .env file
    create_env_file || {
        print_error "Failed to create .env file"
        exit 1
    }
    
    # Set permissions
    chmod 700 "$SCRIPT_DIR"
    chmod 700 "$LOGS_DIR"
    
    # Create service account (best effort)
    create_service_account || true
    
    # Create wrapper script
    create_wrapper_script || {
        print_error "Failed to create wrapper script"
        exit 1
    }
    
    # Print summary
    print_summary
}

# Run main
main "$@"
