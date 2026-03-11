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

WORKDIR ${APP_DIR}
COPY . ${APP_DIR}

# UV as a build manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
# Don't collect usage data (Why is this the default to begin with...)
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Export env.env for login and non-interactive bash shells.
RUN cat > /etc/profile.d/artifact-env.sh <<EOF
set -a
source "${APP_DIR}/env.env"
set +a
EOF
ENV BASH_ENV=/etc/profile.d/artifact-env.sh

# Build snapshots and Python environments used by the artifact.
RUN scripts/setup/1_build_cpython.sh --jobs ${CPYTHON_MAKE_JOBS}
RUN scripts/setup/2_build_venv.sh
RUN scripts/setup/3_pyperformance_setup.sh

RUN scripts/smoketest.sh --minimal

EXPOSE 8501
ENTRYPOINT ["/bin/bash","-lc","source \"$STABLE_PYTHON_ENV_ACTIVATE\" && python -m streamlit run app/immutability/artifact.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true"]

# ENV SHELL=/bin/bash
# CMD ["/bin/bash", "-lc", "exec /bin/bash"]
