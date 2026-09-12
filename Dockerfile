# syntax=docker/dockerfile:1

# AWS Lambda container image running the free-threaded (no-GIL) CPython 3.14t
# TonIO implementation. Built for arm64 (Lambda Graviton).
#
# Runtime base is Amazon Linux 2023 - the OS AWS Lambda itself uses. AL2023
# ships no perl (so it is unaffected by CVE-2026-13221) and receives regular
# AWS security patching. The official docker `python` image has no
# free-threaded tag, so the interpreter is still built via uv in a builder
# stage. AL2023 provides glibc 2.34, satisfying the manylinux_2_17 wheels used
# by tonio and awslambdaric.

ARG FUNCTION_DIR="/function"
ARG PYTHON_VERSION="3.14"
ARG UV_VERSION="0.9.27"

# ---- build stage: create a free-threaded interpreter with all dependencies ---
FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS build

ARG FUNCTION_DIR
ARG PYTHON_VERSION
ARG UV_VERSION

# Install uv (provides free-threaded CPython builds + the installer) via the
# official standalone installer, pinned for reproducibility.
RUN dnf install -y --setopt=install_weak_deps=False ca-certificates tar gzip which \
    && dnf clean all
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

# Strip build-time installer tooling (pip, setuptools, wheel) from the
# interpreter now that dependencies are installed. These tools are only needed
# during the build; the Lambda runtime invokes awslambdaric and never uses
# them. Removing them here keeps the runtime image minimal and free of their
# SBOM-driven CVEs (e.g. pip CVE-2026-13346). Done in the build stage so the
# runtime stage copies only the minimal interpreter.
RUN set -e; \
    for sp in /opt/python/*/lib/python3.14t/site-packages; do \
        rm -rf "$sp"/pip "$sp"/pip-* \
               "$sp"/setuptools "$sp"/setuptools-* "$sp"/pkg_resources \
               "$sp"/wheel "$sp"/wheel-*; \
    done; \
    for b in /opt/python/*/bin; do \
        rm -f "$b"/pip "$b"/pip3 "$b"/pip3.* "$b"/wheel; \
    done

# ---- runtime stage --------------------------------------------------------
FROM public.ecr.aws/amazonlinux/amazonlinux:2023

ARG FUNCTION_DIR

# Apply the latest AL2023 security updates. No perl is present on this base.
RUN dnf upgrade -y --setopt=install_weak_deps=False \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# Bring only the minimal free-threaded interpreter and installed dependencies
# over from the build stage (build-time tooling was already stripped there).
COPY --from=build /opt/python /opt/python
COPY --from=build ${FUNCTION_DIR} ${FUNCTION_DIR}

# Put the uv-managed free-threaded python on PATH as `python`. Resolve the
# interpreter via a shell glob so the minimal runtime needs no `find`.
RUN set -e; \
    py="$(ls /opt/python/*/bin/python3.14t 2>/dev/null | head -n1)"; \
    ln -s "$py" /usr/local/bin/python

WORKDIR ${FUNCTION_DIR}

# Ensure the GIL stays disabled (free-threaded builds honor PYTHON_GIL=0).
ENV PYTHON_GIL=0
ENV PYTHONPATH=${FUNCTION_DIR}

# awslambdaric is the Lambda Runtime Interface Client; CMD names the handler.
ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["lambda_function_ft.lambda_handler"]
