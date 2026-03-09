FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG APP_DIR=/artifact
ARG CPYTHON_MAKE_JOBS=4
ENV APP_DIR=${APP_DIR}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# CPython build dependencies for Linux (Ubuntu).
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		bash \
		build-essential \
		ca-certificates \
		curl \
		git \
		lcov \
		python3 \
		python3-venv \
		libbz2-dev \
		libdb5.3-dev \
		libexpat1-dev \
		libffi-dev \
		libgdbm-dev \
		liblzma-dev \
		libncursesw5-dev \
		libreadline-dev \
		libsqlite3-dev \
		libssl-dev \
		pkg-config \
		tk-dev \
		uuid-dev \
		wget \
		xz-utils \
		zlib1g-dev \
	&& rm -rf /var/lib/apt/lists/*

# Validate that python3 is available.
RUN python3 --version

WORKDIR ${APP_DIR}
COPY . ${APP_DIR}

# Build both CPython snapshots in the image.
RUN scripts/build_cpython.sh --jobs ${CPYTHON_MAKE_JOBS}

# Export values from snapshots/snapshot-sources.env as process environment variables.
RUN cat > /etc/profile.d/snapshot-sources.sh <<EOF
set -a
source "${APP_DIR}/snapshots/snapshot-sources.env"
set +a
EOF

# Interactive website (optional)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# uv installs to ~/.local/bin by default
ENV PATH="/root/.local/bin:${PATH}"

# Don't collect usage data (Why is this the default to begin with...)
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR "${APP_DIR}/app/immutability"

RUN uv python install && \
    uv venv && \
    uv sync

EXPOSE 8501
ENTRYPOINT ["/bin/bash","-lc","source /etc/profile.d/snapshot-sources.sh && exec .venv/bin/python -m streamlit run artifact.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true"]

# ENV SHELL=/bin/bash
# CMD ["/bin/bash", "-lc", "source /etc/profile.d/snapshot-sources.sh && exec /bin/bash"]
