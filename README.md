# Metabase MCP Server 🚀

A high-performance Model Context Protocol (MCP) server for Metabase, built with FastMCP and Python. This server enables AI assistants like Claude and Cursor to interact seamlessly with your Metabase instance, providing powerful database analytics and visualization capabilities.

## ✨ Key Features

### Database Operations
- **List Databases**: Browse all configured Metabase databases
- **Table Discovery**: Explore tables with metadata and descriptions
- **Field Inspection**: Get detailed field/column information with smart pagination

### Query & Analytics
- **SQL Execution**: Run native SQL queries with parameter support
- **Card Management**: Execute, create, and manage Metabase questions/cards
- **Collection Organization**: Create and manage collections for better organization

### Authentication & Security
- **API Key Support**: Secure authentication via Metabase API keys (recommended)
- **Session-based Auth**: Alternative email/password authentication
- **Environment Variables**: Secure credential management via `.env` files

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Metabase instance with API access
- uv package manager (recommended) or pip

### Installation

#### Using uv (Recommended)
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/yourusername/metabase-mcp.git
cd metabase-mcp

# Install dependencies
uv sync
```

#### Using pip
```bash
# Clone and install
git clone https://github.com/yourusername/metabase-mcp.git
cd metabase-mcp
pip install -r requirements.txt
```

## ⚙️ Configuration

Create a `.env` file with your Metabase credentials:

```bash
cp .env.example .env
```

### Configuration Options

#### Option 1: API Key Authentication (Recommended)
```env
METABASE_URL=https://your-metabase-instance.com
METABASE_API_KEY=your-api-key-here
```

#### Option 2: Email/Password Authentication
```env
METABASE_URL=https://your-metabase-instance.com
METABASE_USER_EMAIL=your-email@example.com
METABASE_PASSWORD=your-password
```

#### Optional: Custom Host/Port for SSE/HTTP
```env
HOST=localhost  # Default: 0.0.0.0
PORT=9000      # Default: 8000
```

## Usage

### Run the Server

```bash
# STDIO transport (default)
uv run python server.py

# SSE transport (uses HOST=0.0.0.0, PORT=8000 by default)
uv run python server.py --sse

# HTTP transport (uses HOST=0.0.0.0, PORT=8000 by default)
uv run python server.py --http

# Custom host and port via environment variables
HOST=localhost PORT=9000 uv run python server.py --sse
HOST=192.168.1.100 PORT=8080 uv run python server.py --http

# Set environment variables persistently
export HOST=localhost
export PORT=9000
uv run python server.py --sse
```

### FastMCP CLI Integration

```bash
# Run with FastMCP CLI
fastmcp run server.py

# Install as Claude Desktop MCP server
fastmcp install server.py -n "Metabase MCP"
```

### Cursor Integration

For Cursor IDE integration:

#### STDIO Transport (Default)
```bash
uv run python scripts/install-cursor.py
```

#### SSE Transport
```bash
# Install with SSE transport
uv run python scripts/install-cursor.py --sse        # Port 8000 (default)
uv run python scripts/install-cursor.py --sse 9000   # Custom port

# Or use the dedicated SSE installer
uv run python scripts/install-cursor-sse.py          # Port 8000
uv run python scripts/install-cursor-sse.py 9000     # Custom port
```

**Important for SSE**: You must start the server before using Cursor:
```bash
uv run python server.py --sse 8000
```

### Claude Integration
After running `uv sync`, you can find the Python executable at `/path/to/repo/.venv/bin/python`.
To integrate with Claude, add or update the configuration file at `~/Library/Application\ Support/Claude/claude_desktop_config.json`:
```json
{
    "mcpServers": {
        "metabase-mcp-server": {
            "command": "/path/to/repo/.venv/bin/python",
            "args": ["/path/to/repo/server.py"]
        }
    }
}
```

## 🛠️ Available Tools

### Database Operations
| Tool | Description |
|------|------------|
| `list_databases` | List all configured databases in Metabase |
| `list_tables` | Get all tables in a specific database with metadata |
| `get_table_fields` | Retrieve field/column information for a table |

### Query Operations
| Tool | Description |
|------|------------|
| `execute_query` | Execute native SQL queries with parameter support |
| `execute_card` | Run saved Metabase questions/cards |

### Card Management
| Tool | Description |
|------|------------|
| `list_cards` | List all saved questions/cards |
| `create_card` | Create new questions/cards with SQL queries |

### Collection Management
| Tool | Description |
|------|------------|
| `list_collections` | Browse all collections |
| `create_collection` | Create new collections for organization |

## Transport Methods

The server supports multiple transport methods:

- **STDIO** (default): For IDE integration (Cursor, Claude Desktop)
- **SSE**: Server-Sent Events for web applications
- **HTTP**: Standard HTTP for API access

```bash
uv run python server.py                        # STDIO (default)
uv run python server.py --sse                  # SSE (HOST=0.0.0.0, PORT=8000)
uv run python server.py --http                 # HTTP (HOST=0.0.0.0, PORT=8000)
HOST=localhost PORT=9000 uv run python server.py --sse   # Custom host/port
```

## 🧪 Development

### Setup Development Environment

```bash
# Install with dev dependencies
uv sync --group dev

# Or with pip
pip install -r requirements-dev.txt
```

### Code Quality

```bash
# Run linting
uv run ruff check .

# Format code
uv run ruff format .

# Type checking
uv run mypy server.py

# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=server --cov-report=html
```

### Validation

```bash
# Validate server setup
uv run python scripts/validate.py
```

## 📚 Examples

### Query Examples

```python
# List all databases
databases = await list_databases()

# Execute a SQL query
result = await execute_query(
    database_id=1,
    query="SELECT * FROM users LIMIT 10"
)

# Create and run a card
card = await create_card(
    name="Active Users Report",
    database_id=1,
    query="SELECT COUNT(*) FROM users WHERE active = true",
    collection_id=2
)
```

### Example Files
- `examples/quick-start.py` - Getting started guide
- `examples/examples.py` - Common usage patterns  
- `examples/sse-example.py` - SSE transport demo

## 📁 Project Structure

```
metabase-mcp/
├── server.py                 # Main MCP server implementation
├── pyproject.toml           # Project configuration and dependencies
├── .env.example             # Environment variables template
├── scripts/
│   ├── install-cursor.py    # Cursor IDE installer
│   ├── install-cursor-sse.py # SSE-specific installer
│   └── validate.py          # Installation validator
├── examples/                # Usage examples
├── tests/                   # Test suite
└── docs/                    # Additional documentation
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Metabase API Documentation](https://www.metabase.com/docs/latest/api-documentation) 
