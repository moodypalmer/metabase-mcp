#!/bin/bash

# Automated Cursor MCP Installation Script for Metabase FastMCP

set -e  # Exit on any error

echo "🚀 Installing Metabase FastMCP for Cursor..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

print_success "uv is installed"

# Install dependencies
print_status "Installing Python dependencies with uv..."
uv sync

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your Metabase configuration"
    else
        print_status "Creating basic .env file..."
        cat > .env << EOF
# Metabase Configuration
METABASE_URL=http://localhost:3000
METABASE_USER_EMAIL=your-email@example.com
METABASE_PASSWORD=your-password
METABASE_API_KEY=your-api-key

# Either use API_KEY or EMAIL+PASSWORD for authentication
# API_KEY takes precedence if both are provided
EOF
        print_warning "Please edit .env file with your Metabase configuration"
    fi
else
    print_success ".env file already exists"
fi

# Detect Cursor configuration directory
CURSOR_CONFIG_DIR=""

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CURSOR_CONFIG_DIR="$HOME/Library/Application Support/Cursor/User"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    CURSOR_CONFIG_DIR="$HOME/.config/Cursor/User"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows
    CURSOR_CONFIG_DIR="$APPDATA/Cursor/User"
fi

if [ -z "$CURSOR_CONFIG_DIR" ]; then
    print_error "Could not detect Cursor configuration directory for your OS"
    print_status "Please manually add the configuration to your Cursor settings"
    cat cursor-config.json
    exit 1
fi

# Check if Cursor config directory exists
if [ ! -d "$CURSOR_CONFIG_DIR" ]; then
    print_error "Cursor configuration directory not found: $CURSOR_CONFIG_DIR"
    print_status "Please make sure Cursor is installed and has been run at least once"
    exit 1
fi

CURSOR_SETTINGS_FILE="$CURSOR_CONFIG_DIR/settings.json"

# Get current working directory for absolute path
CURRENT_DIR=$(pwd)

# Create the MCP configuration
MCP_CONFIG=$(cat << EOF
{
  "mcpServers": {
    "metabase": {
      "command": "uv",
      "args": ["run", "python", "server.py"],
      "cwd": "$CURRENT_DIR",
      "env": {
        "METABASE_URL": "http://localhost:3000",
        "METABASE_API_KEY": "your-api-key-here"
      }
    }
  }
}
EOF
)

# Check if settings.json exists
if [ ! -f "$CURSOR_SETTINGS_FILE" ]; then
    print_status "Creating new Cursor settings.json file..."
    echo "$MCP_CONFIG" > "$CURSOR_SETTINGS_FILE"
    print_success "MCP configuration added to Cursor settings"
else
    # Check if mcpServers already exists in settings
    if grep -q '"mcpServers"' "$CURSOR_SETTINGS_FILE"; then
        print_warning "mcpServers configuration already exists in Cursor settings"
        print_status "Please manually merge the following configuration:"
        echo "$MCP_CONFIG"
    else
        # Add mcpServers to existing settings
        print_status "Adding MCP configuration to existing Cursor settings..."
        
        # Create a temporary file with the merged configuration
        python3 -c "
import json
import sys

# Read existing settings
with open('$CURSOR_SETTINGS_FILE', 'r') as f:
    settings = json.load(f)

# Add MCP configuration
mcp_config = {
    'mcpServers': {
        'metabase': {
            'command': 'uv',
            'args': ['run', 'python', 'server.py'],
            'cwd': '$CURRENT_DIR',
            'env': {
                'METABASE_URL': 'http://localhost:3000',
                'METABASE_API_KEY': 'your-api-key-here'
            }
        }
    }
}

settings.update(mcp_config)

# Write back to file
with open('$CURSOR_SETTINGS_FILE', 'w') as f:
    json.dump(settings, f, indent=2)

print('MCP configuration merged successfully')
" 2>/dev/null || {
            print_warning "Could not automatically merge configuration"
            print_status "Please manually add the following to your Cursor settings.json:"
            echo "$MCP_CONFIG"
        }
    fi
fi

print_success "Installation completed!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your Metabase configuration"
echo "2. Restart Cursor to load the new MCP server"
echo "3. The Metabase MCP tools will be available in Cursor's AI chat"
echo ""
echo "🧪 Test the installation:"
echo "  uv run python validate.py"
echo ""
echo "🔧 Manual configuration (if needed):"
echo "  Add to Cursor settings.json:"
echo "$MCP_CONFIG" 