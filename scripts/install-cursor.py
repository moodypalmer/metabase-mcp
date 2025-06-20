#!/usr/bin/env python3
"""
Cross-platform Cursor MCP Installation Script for Metabase FastMCP
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def print_status(message):
    print(f"[INFO] {message}")


def print_success(message):
    print(f"[SUCCESS] {message}")


def print_warning(message):
    print(f"[WARNING] {message}")


def print_error(message):
    print(f"[ERROR] {message}")


def check_uv_installed():
    """Check if uv is installed"""
    if not shutil.which("uv"):
        print_error("uv is not installed. Please install uv first:")
        print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("  or visit: https://docs.astral.sh/uv/getting-started/installation/")
        return False
    print_success("uv is installed")
    return True


def install_dependencies():
    """Install Python dependencies with uv"""
    print_status("Installing Python dependencies with uv...")
    try:
        subprocess.run(["uv", "sync"], check=True)
        print_success("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False


def setup_env_file():
    """Set up .env file"""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print_success(".env file already exists")
        return True

    env_content = """# Metabase Configuration
METABASE_URL=http://localhost:3000
METABASE_USER_EMAIL=your-email@example.com
METABASE_PASSWORD=your-password
METABASE_API_KEY=your-api-key

# Either use API_KEY or EMAIL+PASSWORD for authentication
# API_KEY takes precedence if both are provided
"""

    if env_example.exists():
        print_status("Creating .env file from template...")
        shutil.copy(env_example, env_file)
    else:
        print_status("Creating basic .env file...")
        with open(env_file, "w") as f:
            f.write(env_content)

    print_warning("Please edit .env file with your Metabase configuration")
    return True


def get_cursor_config_dir():
    """Get Cursor configuration directory based on OS"""
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Cursor" / "User"
    elif system == "Linux":
        return Path.home() / ".config" / "Cursor" / "User"
    elif system == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "Cursor" / "User"
        else:
            return Path.home() / "AppData" / "Roaming" / "Cursor" / "User"
    else:
        return None


def create_mcp_config(transport="stdio", port=8000):
    """Create MCP configuration"""
    current_dir = Path.cwd().absolute()

    if transport == "sse":
        return {
            "mcpServers": {
                "metabase": {
                    "url": f"http://localhost:{port}/sse",
                    "env": {
                        "METABASE_URL": "http://localhost:3000",
                        "METABASE_API_KEY": "your-api-key-here",
                    },
                }
            }
        }
    else:
        return {
            "mcpServers": {
                "metabase": {
                    "command": "uv",
                    "args": ["run", "python", "server.py"],
                    "cwd": str(current_dir),
                    "env": {
                        "METABASE_URL": "http://localhost:3000",
                        "METABASE_API_KEY": "your-api-key-here",
                    },
                }
            }
        }


def install_cursor_config(transport="stdio", port=8000):
    """Install MCP configuration to Cursor"""
    cursor_config_dir = get_cursor_config_dir()

    if not cursor_config_dir:
        print_error("Could not detect Cursor configuration directory for your OS")
        print_status("Please manually add the configuration to your Cursor settings")
        print(json.dumps(create_mcp_config(transport, port), indent=2))
        return False

    if not cursor_config_dir.exists():
        print_error(f"Cursor configuration directory not found: {cursor_config_dir}")
        print_status("Please make sure Cursor is installed and has been run at least once")
        return False

    settings_file = cursor_config_dir / "settings.json"
    mcp_config = create_mcp_config(transport, port)

    if not settings_file.exists():
        print_status("Creating new Cursor settings.json file...")
        with open(settings_file, "w") as f:
            json.dump(mcp_config, f, indent=2)
        print_success("MCP configuration added to Cursor settings")
    else:
        # Read existing settings
        try:
            with open(settings_file) as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            print_error("Invalid JSON in existing settings.json")
            return False

        if "mcpServers" in settings:
            print_warning("mcpServers configuration already exists in Cursor settings")
            print_status("Please manually merge the following configuration:")
            print(json.dumps(mcp_config, indent=2))
            return False
        else:
            print_status("Adding MCP configuration to existing Cursor settings...")
            settings.update(mcp_config)

            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)

            print_success("MCP configuration merged successfully")

    return True


def main():
    """Main installation function"""
    print("🚀 Installing Metabase FastMCP for Cursor...")
    
    # Parse command line arguments
    import sys
    transport = "stdio"
    port = 8000
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--sse":
            transport = "sse"
            if len(sys.argv) > 2:
                port = int(sys.argv[2])
        elif sys.argv[1] == "--help":
            print("Usage: python install-cursor.py [--sse [port]]")
            print("  --sse [port]  Use SSE transport (default port: 8000)")
            print("  --help        Show this help message")
            return True

    print(f"📡 Using {transport.upper()} transport" + (f" on port {port}" if transport == "sse" else ""))

    # Check prerequisites
    if not check_uv_installed():
        return False

    # Install dependencies
    if not install_dependencies():
        return False

    # Setup environment
    if not setup_env_file():
        return False

    # Install Cursor configuration
    if not install_cursor_config(transport, port):
        return False

    print_success("Installation completed!")
    print()
    print("📝 Next steps:")
    print("1. Edit .env file with your Metabase configuration")
    print("2. Restart Cursor to load the new MCP server")
    print("3. The Metabase MCP tools will be available in Cursor's AI chat")
    print()
    print("🧪 Test the installation:")
    print("  uv run python validate.py")
    print()
    if transport == "sse":
        print("🔧 Start the SSE server:")
        print(f"  uv run python server.py --sse {port}")
        print()
        print("⚠️  Important: The SSE server must be running for Cursor to connect!")
        print("   Start the server before using Cursor's AI chat.")
    else:
        print("🔧 Run server manually:")
        print("  uv run python server.py          # STDIO transport")
        print("  uv run python server.py --sse    # SSE transport on port 8000")
        print("  uv run python server.py --http   # HTTP transport on port 8000")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
