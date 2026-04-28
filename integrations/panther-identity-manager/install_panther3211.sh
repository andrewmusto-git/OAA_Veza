#!/bin/bash

################################################################################
# Panther Identity Manager to Veza OAA Integration Installer
#
# This script installs the Panther-Veza integration with all dependencies.
# Run with: curl -fsSL <url> | bash
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/pvolu-vz/OAA_Agent.git"
INSTALL_DIR="${HOME}/panther-veza-integration"
INTEGRATION_DIR="integrations/panther-identity-manager"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Panther Identity Manager to Veza Integration${NC}"
echo -e "${BLUE}Installation Script${NC}"
echo -e "${BLUE}================================================${NC}"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if running on Windows
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    print_error "This script is for Linux/macOS. Windows users should:"
    echo "1. Install Python 3.8+ from python.org"
    echo "2. Clone the repository manually"
    echo "3. Create venv: python -m venv venv"
    echo "4. Activate venv: venv\\Scripts\\activate"
    echo "5. Install dependencies: pip install -r requirements.txt"
    exit 1
fi

# Check system dependencies
print_info "Checking system dependencies..."

if ! command -v python3 &> /dev/null; then
    print_warning "Python 3 not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3 python3-pip
    elif command -v brew &> /dev/null; then
        brew install python3
    else
        print_error "Could not install Python 3. Please install manually and try again."
        exit 1
    fi
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
print_success "Python 3 found: $PYTHON_VERSION"

if ! command -v git &> /dev/null; then
    print_warning "Git not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y git
    elif command -v yum &> /dev/null; then
        sudo yum install -y git
    elif command -v brew &> /dev/null; then
        brew install git
    else
        print_error "Could not install Git. Please install manually and try again."
        exit 1
    fi
fi

print_success "Git found: $(git --version)"

# Create installation directory
print_info "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Clone repository or update existing
if [ -d ".git" ]; then
    print_info "Updating existing repository..."
    git pull origin main
else
    print_info "Cloning repository..."
    git clone "$REPO_URL" .
fi

print_success "Repository ready"

# Change to integration directory
cd "$INTEGRATION_DIR"

# Create Python virtual environment
print_info "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
print_info "Installing Python dependencies..."
pip install -r requirements.txt

print_success "Dependencies installed"

# Create logs directory
mkdir -p logs

# Prompt for configuration
print_info "Configuring Panther connection..."
echo

read -p "Enter Panther API Base URL [https://mill-mes-security.westrock.com]: " PANTHER_URL
PANTHER_URL=${PANTHER_URL:-"https://mill-mes-security.westrock.com"}

read -p "Enter Panther OAuth2 Client ID: " CLIENT_ID
while [ -z "$CLIENT_ID" ]; do
    print_error "Client ID is required"
    read -p "Enter Panther OAuth2 Client ID: " CLIENT_ID
done

read -sp "Enter Panther OAuth2 Client Secret: " CLIENT_SECRET
echo
while [ -z "$CLIENT_SECRET" ]; do
    print_error "Client Secret is required"
    read -sp "Enter Panther OAuth2 Client Secret: " CLIENT_SECRET
    echo
done

read -p "Enter Panther Tenant ID [3211]: " TENANT_ID
TENANT_ID=${TENANT_ID:-"3211"}

echo
print_info "Configuring Veza connection..."
echo

read -p "Enter Veza API URL: " VEZA_URL
while [ -z "$VEZA_URL" ]; do
    print_error "Veza URL is required"
    read -p "Enter Veza API URL: " VEZA_URL
done

read -sp "Enter Veza API Key: " VEZA_API_KEY
echo
while [ -z "$VEZA_API_KEY" ]; do
    print_error "Veza API Key is required"
    read -sp "Enter Veza API Key: " VEZA_API_KEY
    echo
done

# Create .env file
print_info "Creating configuration file (.env)..."
cat > .env << EOF
# Panther Configuration
PANTHER_BASE_URL=$PANTHER_URL
PANTHER_CLIENT_ID=$CLIENT_ID
PANTHER_CLIENT_SECRET=$CLIENT_SECRET
PANTHER_TENANT_ID=$TENANT_ID

# Veza Configuration
VEZA_URL=$VEZA_URL
VEZA_API_KEY=$VEZA_API_KEY
EOF

chmod 600 .env
print_success "Configuration file created: .env"

# Test connection
echo
print_info "Testing Panther connection..."
if python panther.py --test --config .env; then
    print_success "Panther connection successful"
else
    print_warning "Panther connection test failed. Please verify credentials."
fi

# Create wrapper script
print_info "Creating integration wrapper script..."
SCRIPT_DIR=$(pwd)
cat > panther-veza-sync.sh << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
source venv/bin/activate
python panther.py --config .env
EOF

chmod +x panther-veza-sync.sh
print_success "Wrapper script created: panther-veza-sync.sh"

# Summary
echo
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo
echo "Installation directory: $INSTALL_DIR"
echo "Integration directory: $INSTALL_DIR/$INTEGRATION_DIR"
echo
echo "To run the integration:"
echo "  cd $INSTALL_DIR/$INTEGRATION_DIR"
echo "  source venv/bin/activate"
echo "  python panther.py --config .env"
echo
echo "Or use the wrapper script:"
echo "  cd $INSTALL_DIR/$INTEGRATION_DIR"
echo "  ./panther-veza-sync.sh"
echo
echo "To schedule with cron (run at 2 AM daily):"
echo "  crontab -e"
echo "  # Add this line:"
echo "  0 2 * * * cd $INSTALL_DIR/$INTEGRATION_DIR && ./panther-veza-sync.sh >> logs/cron.log 2>&1"
echo
echo "Configuration file: $INSTALL_DIR/$INTEGRATION_DIR/.env"
echo "Logs: $INSTALL_DIR/$INTEGRATION_DIR/logs/"
echo
print_success "Installation script complete!"
