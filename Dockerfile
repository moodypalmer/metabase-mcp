FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml .
COPY requirements.txt .

# Install Python dependencies with uv
RUN uv sync --frozen

# Copy application code
COPY server.py .
COPY .env* ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port (for HTTP/SSE transport)
EXPOSE 8000

# Default command
CMD ["uv", "run", "python", "server.py"] 