#!/usr/bin/env python3
"""
Install Metabase FastMCP for Cursor with SSE transport
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Install with SSE transport"""
    print("🌐 Installing Metabase FastMCP for Cursor (SSE Transport)")
    print("=" * 60)
    
    # Parse port argument
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid port number. Using default port 8000.")
    
    print(f"📡 Configuring SSE transport on port {port}")
    
    # Run the main installer with SSE flag
    try:
        cmd = [sys.executable, "install-cursor.py", "--sse", str(port)]
        subprocess.run(cmd, check=True)
        
        print("\n" + "=" * 60)
        print("🎉 SSE installation completed!")
        print()
        print("📋 Next steps:")
        print("1. Edit .env file with your Metabase configuration")
        print(f"2. Start the SSE server: uv run python server.py --sse {port}")
        print("3. Restart Cursor")
        print("4. The server must be running when using Cursor's AI chat")
        print()
        print("💡 Pro tip: Run the server in a separate terminal:")
        print(f"   Terminal 1: uv run python server.py --sse {port}")
        print("   Terminal 2: Open Cursor and use AI chat")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ install-cursor.py not found. Make sure you're in the correct directory.")
        return False

if __name__ == "__main__":
    main() 