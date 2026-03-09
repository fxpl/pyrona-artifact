FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG APP_DIR=/opt/pyrona-artifact
ENV APP_DIR=${APP_DIR}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# CPython build dependencies for Linux (Ubuntu).
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		bash \
		build-essential \
		ca-certificates \
		git \
		lcov \
		python3.14 \
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

WORKDIR ${APP_DIR}
COPY . ${APP_DIR}

# Build both CPython snapshots in the image.
RUN scripts/build_cpython.sh

# Export values from snapshots/snapshot-sources.env as process environment variables.
RUN cat > /etc/profile.d/snapshot-sources.sh <<EOF
set -a
source "${APP_DIR}/snapshots/snapshot-sources.env"
set +a
EOF

# Interactive website (optional)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Don't collect usage data (Why is this the default to begin with...)
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

ENV SHELL=/bin/bash
CMD ["/bin/bash", "-lc", "source /etc/profile.d/snapshot-sources.sh && exec /bin/bash"]
