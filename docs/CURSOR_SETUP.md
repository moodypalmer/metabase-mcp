# Cursor MCP Setup Guide

This guide shows you how to quickly add the Metabase FastMCP server to Cursor IDE.

## 🚀 Quick Setup (Automated)

### Option 1: Python Script (Cross-platform)
```bash
uv run python install-cursor.py
```

### Option 2: Bash Script (Linux/macOS)
```bash
./install-cursor.sh
```

Both scripts will:
- ✅ Check if `uv` is installed
- ✅ Install Python dependencies with `uv sync`
- ✅ Create `.env` configuration file
- ✅ Detect your Cursor configuration directory
- ✅ Add MCP server configuration to Cursor settings
- ✅ Provide next steps

## 🔧 Manual Setup

If you prefer to set up manually or the automated scripts don't work:

### 1. Install Dependencies
```bash
uv sync
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Metabase settings
```

### 3. Find Cursor Settings Location

**macOS:**
```
~/Library/Application Support/Cursor/User/settings.json
```

**Linux:**
```
~/.config/Cursor/User/settings.json
```

**Windows:**
```
%APPDATA%\Cursor\User\settings.json
```

### 4. Add MCP Configuration

Add this to your Cursor `settings.json`:

```json
{
  "mcpServers": {
    "metabase": {
      "command": "uv",
      "args": ["run", "python", "server.py"],
      "cwd": "/absolute/path/to/python-fastmcp",
      "env": {
        "METABASE_URL": "http://localhost:3000",
        "METABASE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**Important:** Replace `/absolute/path/to/python-fastmcp` with the actual absolute path to this directory.

## 🌐 Transport Options

The server supports multiple transport methods:

### STDIO (Default - for Cursor)
```json
{
  "command": "uv",
  "args": ["run", "python", "server.py"]
}
```

### SSE Transport (Better Performance)
For SSE transport with Cursor, use a URL-based configuration:

```json
{
  "url": "http://localhost:8000/sse",
  "env": {
    "METABASE_URL": "http://localhost:3000",
    "METABASE_API_KEY": "your-api-key-here"
  }
}
```

**Important for SSE**: You must start the server separately:
```bash
uv run python server.py --sse 8000
```

### Quick SSE Setup
Use the automated SSE installer:
```bash
uv run python install-cursor-sse.py
```

### STDIO vs SSE Comparison

| Aspect | STDIO | SSE |
|--------|-------|-----|
| **Setup** | Automatic | Requires running server |
| **Performance** | Good | Better (persistent connection) |
| **Debugging** | Harder | Easier (can test with curl) |
| **Resource Usage** | Higher | Lower |
| **Reliability** | More robust | Network dependent |

**Recommendation**: Use SSE for active development, STDIO for occasional use.

## 🧪 Testing Your Setup

### 1. Validate Installation
```bash
uv run python validate.py
```

### 2. Test Server Directly
```bash
uv run python test_server.py
```

### 3. Test SSE Transport (if using)
```bash
# Terminal 1: Start SSE server
uv run python server.py --sse

# Terminal 2: Test connection
uv run python sse-example.py
```

## 🔄 After Setup

1. **Restart Cursor** to load the new MCP server
2. **Open Cursor's AI chat** (Cmd/Ctrl + L)
3. **Test the integration** by asking: "List the Metabase databases"

The AI should now have access to all 9 Metabase tools:
- `list_databases`
- `list_cards` 
- `execute_card`
- `execute_query`
- `create_card`
- `list_collections`
- `create_collection`
- `list_tables`
- `get_table_fields`

## 🛠️ Troubleshooting

### "uv not found"
Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### "Cannot connect to Metabase"
1. Check your `.env` file configuration
2. Ensure Metabase is running and accessible
3. Verify API key or credentials are correct

### "MCP server not loading in Cursor"
1. Check Cursor settings.json syntax is valid JSON
2. Ensure the `cwd` path is absolute and correct
3. Restart Cursor completely
4. Check Cursor's developer console for errors

### "Permission denied"
Make sure scripts are executable:
```bash
chmod +x install-cursor.py install-cursor.sh
```

## 📝 Configuration Examples

### Using API Key (Recommended)
```bash
METABASE_URL=https://your-metabase.com
METABASE_API_KEY=mb_your_api_key_here
```

### Using Email/Password
```bash
METABASE_URL=https://your-metabase.com
METABASE_USER_EMAIL=your@email.com
METABASE_PASSWORD=your_password
```

### Custom Port/Host
```bash
METABASE_URL=http://metabase.local:3001
METABASE_API_KEY=your_key
```

## 🔗 Integration Benefits

Once set up, you can:
- 📊 Query Metabase data directly from Cursor's AI chat
- 🔍 Explore database schemas and tables
- 📈 Create and execute custom SQL queries
- 📋 Manage Metabase cards and collections
- 🤖 Let AI help analyze your data through natural language

The AI assistant becomes your intelligent Metabase companion! 🎉 