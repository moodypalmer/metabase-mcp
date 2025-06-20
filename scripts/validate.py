#!/usr/bin/env python3
"""
Validation script for the Metabase FastMCP server
Tests server structure and tool definitions without requiring Metabase connection
"""

import asyncio
import os
import sys
from pathlib import Path

# Temporarily disable environment validation for testing
os.environ.setdefault("METABASE_URL", "http://localhost:3000")
os.environ.setdefault("METABASE_API_KEY", "test-key")


async def validate_server_structure():
    """Validate that the server loads correctly and has expected tools"""
    print("🔍 Validating Metabase FastMCP Server Structure...")

    try:
        # Import server components
        from fastmcp import Client

        from server import mcp

        print("✅ Server imports successful")

        # Test server creation
        print(f"✅ Server name: {mcp.name}")

        # Create a test client
        async with Client(mcp) as client:
            # List available tools
            tools = await client.list_tools()
            print(f"✅ Found {len(tools)} tools:")

            expected_tools = {
                "list_databases",
                "list_cards",
                "execute_card",
                "execute_query",
                "create_card",
                "list_collections",
                "create_collection",
                "list_tables",
                "get_table_fields",
            }

            found_tools = {tool.name for tool in tools}

            # Check if all expected tools are present
            missing_tools = expected_tools - found_tools
            extra_tools = found_tools - expected_tools

            if missing_tools:
                print(f"❌ Missing tools: {missing_tools}")
                return False

            if extra_tools:
                print(f"ℹ️  Extra tools found: {extra_tools}")

            # Display tool information
            for tool in tools:
                print(f"   • {tool.name}: {tool.description}")

            print("✅ All expected tools are present")

        return True

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False


def validate_file_structure():
    """Validate that all required files are present"""
    print("\n📁 Validating File Structure...")

    required_files = [
        "server.py",
        "requirements.txt",
        "README.md",
        ".env.example",
        "test_server.py",
        "setup.py",
        "examples.py",
        "MIGRATION.md",
        "Dockerfile",
        "docker-compose.yml",
    ]

    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
        else:
            print(f"✅ {file}")

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False

    print("✅ All required files are present")
    return True


def validate_dependencies():
    """Validate that dependencies can be imported"""
    print("\n📦 Validating Dependencies...")

    # Check Python version
    import sys

    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    dependencies = [
        ("fastmcp", "FastMCP"),
        ("httpx", "httpx"),
        ("dotenv", "python-dotenv"),
        ("pydantic", "pydantic"),
    ]

    missing_deps = []
    for module, package in dependencies:
        try:
            __import__(module)
            print(f"✅ {package}")
        except ImportError:
            missing_deps.append(package)
            print(f"❌ {package} - not installed")

    if missing_deps:
        print("\n💡 Install missing dependencies with:")
        print(f"   pip install {' '.join(missing_deps)}")
        return False

    print("✅ All dependencies are available")
    return True


async def main():
    """Main validation function"""
    print("🚀 Metabase FastMCP Server Validation")
    print("=" * 50)

    success = True

    # Validate file structure
    if not validate_file_structure():
        success = False

    # Validate dependencies
    if not validate_dependencies():
        success = False
        print("\n⚠️  Cannot continue validation without dependencies")
        print("   Run: python setup.py or pip install -r requirements.txt")
        sys.exit(1)

    # Validate server structure
    if not await validate_server_structure():
        success = False

    print("\n" + "=" * 50)

    if success:
        print("🎉 Validation completed successfully!")
        print("\nNext steps:")
        print("1. Configure .env file with your Metabase settings")
        print("2. Run: python server.py")
        print("3. Test with: python test_server.py")
        print("4. Try examples: python examples.py")
    else:
        print("❌ Validation failed. Please address the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
