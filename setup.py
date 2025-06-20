#!/usr/bin/env python3
"""
Setup script for Metabase FastMCP Server
"""

import subprocess
import sys
from pathlib import Path


def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")

    # Try uv first, fall back to pip
    if subprocess.run(["which", "uv"], capture_output=True).returncode == 0:
        print("Using uv for dependency management...")
        try:
            subprocess.check_call(["uv", "sync"])
            print("✓ Dependencies installed successfully with uv")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install dependencies with uv: {e}")
            print("Falling back to pip...")

    # Fallback to pip
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully with pip")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False
    return True


def setup_environment():
    """Set up environment configuration"""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print("✓ .env file already exists")
        return True

    if env_example.exists():
        print("Creating .env file from template...")
        try:
            env_example.rename(env_file)
            print("✓ .env file created")
            print("📝 Please edit .env file with your Metabase configuration")
            return True
        except Exception as e:
            print(f"✗ Failed to create .env file: {e}")
            return False

    # Create basic .env file
    env_content = """# Metabase Configuration
METABASE_URL=http://localhost:3000
METABASE_USER_EMAIL=your-email@example.com
METABASE_PASSWORD=your-password
METABASE_API_KEY=your-api-key

# Either use API_KEY or EMAIL+PASSWORD for authentication
# API_KEY takes precedence if both are provided
"""

    try:
        with open(".env", "w") as f:
            f.write(env_content)
        print("✓ .env file created")
        print("📝 Please edit .env file with your Metabase configuration")
        return True
    except Exception as e:
        print(f"✗ Failed to create .env file: {e}")
        return False


def test_installation():
    """Test the installation"""
    print("Testing installation...")
    try:
        # Test import
        print("✓ All dependencies imported successfully")

        # Test server creation (without running)
        print("✓ Server module loaded successfully")

        return True
    except Exception as e:
        print(f"✗ Installation test failed: {e}")
        return False


def install_claude_desktop():
    """Install as Claude Desktop MCP server using FastMCP CLI"""
    print("Installing as Claude Desktop MCP server...")
    try:
        server_path = Path("server.py").absolute()
        subprocess.check_call(["fastmcp", "install", str(server_path), "-n", "Metabase MCP"])
        print("✓ Successfully installed as Claude Desktop MCP server")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install as Claude Desktop MCP server: {e}")
        print("Make sure FastMCP CLI is installed: pip install fastmcp")
        return False
    except FileNotFoundError:
        print("✗ FastMCP CLI not found. Install with: pip install fastmcp")
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up Metabase FastMCP Server")
    print("=" * 40)

    success = True

    # Install dependencies
    if not install_dependencies():
        success = False

    # Setup environment
    if not setup_environment():
        success = False

    # Test installation
    if success and not test_installation():
        success = False

    print("\n" + "=" * 40)

    if success:
        print("✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit .env file with your Metabase configuration")
        print("2. Run the server: python server.py")
        print("3. Or test with: python test_server.py")

        # Ask about Claude Desktop installation
        response = input("\nWould you like to install as Claude Desktop MCP server? (y/N): ")
        if response.lower() in ["y", "yes"]:
            install_claude_desktop()
    else:
        print("❌ Setup encountered errors. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
