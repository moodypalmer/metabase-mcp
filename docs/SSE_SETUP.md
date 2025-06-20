# SSE Transport Setup for Cursor

This guide explains how to set up the Metabase FastMCP server with SSE (Server-Sent Events) transport for use with Cursor.

## What is SSE Transport?

SSE (Server-Sent Events) is a web standard that allows a server to push data to a client over HTTP. For MCP servers, this means:

- **Persistent connection**: The server runs continuously and Cursor connects to it
- **Better performance**: Faster than spawning processes for each request
- **Real-time updates**: Potential for streaming responses
- **Web-compatible**: Works through firewalls and proxies

## Quick Setup

### 1. Install with SSE Configuration

```bash
# Default port (8000)
uv run python install-cursor-sse.py

# Custom port
uv run python install-cursor-sse.py 9000
```

### 2. Start the SSE Server

```bash
# Start server on default port (8000)
uv run python server.py --sse

# Start server on custom port
uv run python server.py --sse 9000
```

### 3. Use Cursor

1. **Keep the server running** in a terminal
2. Open Cursor
3. Use AI chat - it will connect to your SSE server automatically

## Manual Configuration

If you prefer to configure manually:

### 1. Cursor Configuration

Add this to your Cursor settings (`~/.cursor/settings.json` or similar):

```json
{
  "mcpServers": {
    "metabase": {
      "url": "http://localhost:8000/sse",
      "env": {
        "METABASE_URL": "http://localhost:3000",
        "METABASE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### 2. Environment Setup

Create `.env` file:
```bash
METABASE_URL=http://localhost:3000
METABASE_API_KEY=your-api-key-here
```

## Workflow

### Terminal 1: Start Server
```bash
cd python-fastmcp
uv run python server.py --sse 8000
```

You should see:
```
🚀 Metabase FastMCP Server starting...
📡 Transport: SSE
🌐 Server running on http://localhost:8000
📊 SSE endpoint: http://localhost:8000/sse
✅ Server ready for connections!
```

### Terminal 2: Use Cursor
```bash
cursor your-project/
```

Then use Cursor's AI chat normally. The MCP tools will be available automatically.

## Troubleshooting

### Server Won't Start
```bash
# Check if port is in use
lsof -i :8000

# Try a different port
uv run python server.py --sse 9000
```

### Cursor Can't Connect
1. **Verify server is running**: Check Terminal 1 for server status
2. **Check port**: Make sure Cursor config matches server port
3. **Restart Cursor**: Close and reopen Cursor after config changes
4. **Check logs**: Look for connection errors in Cursor's developer tools

### Environment Issues
```bash
# Validate your setup
uv run python validate.py

# Check environment variables
cat .env
```

## Advantages of SSE vs STDIO

| Feature | STDIO | SSE |
|---------|-------|-----|
| Setup | Simpler | Requires server |
| Performance | Process per request | Persistent connection |
| Debugging | Harder to debug | Easy to test with curl |
| Reliability | More robust | Network dependent |
| Resource usage | Higher (process spawning) | Lower (single process) |

## Testing SSE Connection

You can test the SSE connection manually:

```bash
# Test the SSE endpoint
curl -N -H "Accept: text/event-stream" http://localhost:8000/sse

# Test with a simple MCP message
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

## Advanced Configuration

### Custom Host/Port
```bash
# Bind to all interfaces
uv run python server.py --sse 8000 --host 0.0.0.0

# Use environment variables
export MCP_SSE_PORT=9000
export MCP_SSE_HOST=127.0.0.1
uv run python server.py --sse
```

### Multiple Instances
You can run multiple instances on different ports:

```bash
# Terminal 1: Production Metabase
METABASE_URL=https://prod.metabase.com uv run python server.py --sse 8000

# Terminal 2: Development Metabase  
METABASE_URL=http://localhost:3000 uv run python server.py --sse 8001
```

Then configure multiple servers in Cursor:
```json
{
  "mcpServers": {
    "metabase-prod": {
      "url": "http://localhost:8000/sse"
    },
    "metabase-dev": {
      "url": "http://localhost:8001/sse"
    }
  }
}
```

## Production Deployment

For production use, consider:

### Process Management
```bash
# Using screen
screen -S metabase-mcp
uv run python server.py --sse 8000

# Using tmux
tmux new-session -d -s metabase-mcp 'uv run python server.py --sse 8000'

# Using systemd (create service file)
sudo systemctl enable metabase-mcp
sudo systemctl start metabase-mcp
```

### Docker Deployment
```bash
# Build and run with SSE
docker build -t metabase-mcp .
docker run -p 8000:8000 -e TRANSPORT=sse metabase-mcp
```

### Reverse Proxy (nginx)
```nginx
location /mcp/ {
    proxy_pass http://localhost:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_buffering off;
    proxy_cache off;
}
```

## Summary

SSE transport provides better performance and easier debugging for MCP servers. The key points:

1. **Server must be running** before using Cursor
2. **Use dedicated terminals** for server and development
3. **Check ports and configuration** if connection fails
4. **Consider process management** for production use

For most development use cases, SSE provides a better experience than STDIO transport. 