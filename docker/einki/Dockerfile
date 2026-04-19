FROM python:3.12-slim
# Install uv (Python package manager) via official script
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.local/bin:$PATH"
WORKDIR /app

# Dependency layer — cached until uv.lock or pyproject.toml change.
# --frozen: don't re-resolve, fail if lock is stale relative to pyproject.
# --no-install-project: install deps only, skip einki itself (source
# tree isn't in the image yet at this layer).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Project layer — re-runs on any source change but is cheap (deps are
# already installed; uv only needs to install the local einki package).
COPY . .
RUN uv sync --frozen

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:5000/login || exit 1

CMD ["uv", "run", "einki", "--host", "0.0.0.0"]
