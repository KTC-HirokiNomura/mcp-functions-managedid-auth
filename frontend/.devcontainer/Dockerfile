ARG VARIANT="1"
FROM mcr.microsoft.com/devcontainers/go:${VARIANT}

# Install common tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
 && rm -rf /var/lib/apt/lists/*
