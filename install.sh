#!/bin/bash
# Rastro Installation Script - Daily Use

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
# Auto-detect the project root from this script's location (no hardcoded user paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
VENV_DIR="$PROJECT_DIR/.venv"
BACKUP_DIR="$PROJECT_DIR/backups"
LOG_FILE="$PROJECT_DIR/install.log"

# Logging
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Rastro Installation Script ==="
echo "Starting installation at $(date)"

# Check current directory
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}ERROR: Project directory not found at $PROJECT_DIR${NC}"
    exit 1
fi

cd "$PROJECT_DIR"
echo -e "${GREEN}✓ Changed to project directory${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Python dependencies
install_python_deps() {
    echo "Checking Python dependencies..."
    
    # Check for Python3
    if ! command_exists python3; then
        echo -e "${YELLOW}WARNING: python3 not found, installing...${NC}"
        apt-get update && apt-get install -y python3 python3-pip python3-venv
    fi

    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    else
        echo "Virtual environment already exists, activating..."
    fi

    # Install/upgrade pip
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    
    # Install dependencies from pyproject.toml
    if [ -f "pyproject.toml" ]; then
        echo "Installing Python dependencies from pyproject.toml..."
        pip install -e .[dev]
        echo -e "${GREEN}✓ Python dependencies installed${NC}"
    else
        echo -e "${YELLOW}WARNING: pyproject.toml not found, skipping Python install${NC}"
    fi

    # Install requirements.txt if exists
    if [ -f "requirements.txt" ]; then
        echo "Installing additional dependencies from requirements.txt..."
        pip install -r requirements.txt
        echo -e "${GREEN}✓ Additional requirements installed${NC}"
    fi
}

# Function to install Node.js dependencies
install_nodejs_deps() {
    echo "Checking Node.js dependencies..."
    
    if ! command_exists npm; then
        echo -e "${YELLOW}WARNING: npm not found, installing...${NC}"
        # Try to install npm (platform-specific)
        if command_exists apt-get; then
            apt-get update && apt-get install -y npm
        elif command_exists yum; then
            yum install -y npm
        else
            echo -e "${RED}ERROR: Cannot install npm automatically${NC}"
            return 1
        fi
    fi

    # Install frontend dependencies
    if [ -f "frontend/package.json" ]; then
        echo "Installing frontend dependencies..."
        cd frontend
        npm ci
        cd "$PROJECT_DIR"
        echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
    else
        echo -e "${YELLOW}WARNING: frontend/package.json not found${NC}"
    fi
}

# Function to setup configuration
setup_config() {
    echo "Setting up configuration..."

    # Check for .env
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo -e "${YELLOW}WARNING: .env created from .env.example${NC}"
            echo "Please edit .env with your configuration settings"
        else
            echo -e "${RED}ERROR: No .env or .env.example found${NC}"
            return 1
        fi
    fi

    # Backup existing config if it exists
    if [ -f ".env" ]; then
        mkdir -p "$BACKUP_DIR"
        cp .env "$BACKUP_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"
        echo -e "${GREEN}✓ Configuration backed up${NC}"
    fi

    # Set environment variables
    export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
    echo -e "${GREEN}✓ PYTHONPATH configured${NC}"
}

# Function to initialize database
init_database() {
    echo "Initializing database..."

    if command_exists python3; then
        source "$VENV_DIR/bin/activate"
        
        # Initialize database
        if [ -f "run.py" ]; then
            echo "Running database setup..."
            # Add database commands here when available
            # python run.py --backup
            echo -e "${YELLOW}NOTE: Database setup commands not yet implemented${NC}"
        fi
    fi
}

# Function to verify installation
verify_installation() {
    echo "Verifying installation..."

    source "$VENV_DIR/bin/activate"

    # Test Python imports
    echo "Testing Python imports..."
    python3 -c "import api; print('✓ API imports OK')" 2>/dev/null || echo -e "${RED}✗ Python imports failed${NC}"

    # Test scheduler import (the main fix)
    python3 -c "
from api.scheduler import Scheduler
try:
    # Test scheduler initialization
    print('✓ Scheduler imports OK')
except Exception as e:
    print(f'✗ Scheduler error: {e}')
" 2>/dev/null || echo -e "${RED}✗ Scheduler tests failed${NC}"

    # Test sensor imports
    python3 -c "
try:
    from core.sensors.observation_engine import ObservationEngine
    print('✓ Sensor imports OK')
except Exception as e:
    print(f'✗ Sensor imports failed: {e}')
" 2>/dev/null || echo -e "${RED}✗ Sensor imports failed${NC}"

    echo -e "${GREEN}✓ Installation verification completed${NC}"
}

# Function to create startup script
create_startup_script() {
    echo "Creating startup script..."

    cat > "start.sh" << 'EOF'
#!/bin/bash

# Rastro Startup Script

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

# Activate virtual environment
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "Virtual environment not found. Run install.sh first."
    exit 1
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Start the API server
python3 -m api.main
EOF

    chmod +x start.sh
    echo -e "${GREEN}✓ Startup script created${NC}"
}

# Main installation process
main() {
    echo "Starting Rastro installation process..."

    # Create backups directory
    mkdir -p "$BACKUP_DIR"

    # Step 1: Install Python dependencies
    install_python_deps

    # Step 2: Install Node.js dependencies
    install_nodejs_deps

    # Step 3: Setup configuration
    setup_config

    # Step 4: Initialize database
    init_database

    # Step 5: Create startup script
    create_startup_script

    # Step 6: Verify installation
    verify_installation

    echo ""
    echo -e "${GREEN}=== Installation Complete ===${NC}"
    echo ""
    echo "Next Steps:"
    echo "1. Start the system: ./start.sh"
    echo "2. Check logs: tail -f $LOG_FILE"
    echo "3. Visit the frontend at: http://localhost:3000"
    echo "4. API documentation available in api/ directory"
    echo ""
    echo "Installation log: $LOG_FILE"
}

# Run main installation
main