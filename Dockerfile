# syntax=docker/dockerfile:1

# AWS Lambda container image running the free-threaded (no-GIL) CPython 3.14t
# TonIO implementation. Built for arm64 (Lambda Graviton).
#
# The official docker `python` image has no free-threaded tag, so we install
# free-threaded CPython 3.14t via uv. Debian bookworm ships glibc 2.36, which
# satisfies the manylinux_2_17 wheels used by tonio and awslambdaric.

ARG FUNCTION_DIR="/function"
ARG PYTHON_VERSION="3.14"
ARG UV_VERSION="0.9.27"

# ---- build stage: create a free-threaded interpreter with all dependencies ---
FROM debian:bookworm-slim AS build

ARG FUNCTION_DIR
ARG PYTHON_VERSION
ARG UV_VERSION

# Install uv (provides free-threaded CPython builds + the installer) via the
# official standalone installer, pinned for reproducibility.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
ENV UV_INSTALL_DIR=/usr/local/bin
RUN curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh

# Install the free-threaded CPython build (e.g. 3.14t) into a known location.
ENV UV_PYTHON_INSTALL_DIR=/opt/python
RUN uv python install "${PYTHON_VERSION}t"

WORKDIR /build
COPY requirements-ft.txt ./

# Install the Lambda function's dependencies into the function directory using
# the free-threaded interpreter, so the tonio cp314t wheels are selected.
RUN mkdir -p ${FUNCTION_DIR} && \
    uv pip install \
        --python "${PYTHON_VERSION}t" \
        --target ${FUNCTION_DIR} \
        -r requirements-ft.txt

# Copy in the function source.
COPY src/lambda_function_ft.py ${FUNCTION_DIR}/

# ---- runtime stage --------------------------------------------------------
FROM debian:bookworm-slim

ARG FUNCTION_DIR

# Apply the latest security updates, then remove perl entirely. The Python
# free-threaded Lambda runtime never invokes perl, and Debian bookworm has no
# patched perl-base for CVE-2026-13221 (perl trie regex miscompilation) - only
# sid/unstable is fixed, which is unsuitable for a stable runtime. `perl-base`
# is Debian-Essential but nothing in this image depends on it (verified: apt
# reports perl-base as the only package removed), so we force-remove it to
# eliminate the vulnerable /usr/bin/perl rather than swap to an unstable base.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && dpkg --purge --force-remove-essential perl-base \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Bring the free-threaded interpreter and installed dependencies over.
COPY --from=build /opt/python /opt/python
COPY --from=build ${FUNCTION_DIR} ${FUNCTION_DIR}

# Put the uv-managed free-threaded python on PATH as `python`.
RUN ln -s "$(find /opt/python -name 'python3.14t' -type f | head -n1)" /usr/local/bin/python

WORKDIR ${FUNCTION_DIR}

# Ensure the GIL stays disabled (free-threaded builds honor PYTHON_GIL=0).
ENV PYTHON_GIL=0
ENV PYTHONPATH=${FUNCTION_DIR}

# awslambdaric is the Lambda Runtime Interface Client; CMD names the handler.
ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["lambda_function_ft.lambda_handler"]
