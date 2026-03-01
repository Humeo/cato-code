from __future__ import annotations

import io
import logging

import docker
import docker.errors

logger = logging.getLogger(__name__)

BASE_IMAGE = "repocraft-base:latest"

DOCKERFILE = """\
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \\
    git \\
    curl \\
    wget \\
    build-essential \\
    python3 \\
    python3-pip \\
    python3-venv \\
    python3-dev \\
    nodejs \\
    npm \\
    ca-certificates \\
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:/root/.local/bin:$PATH"

WORKDIR /workspace

CMD ["/bin/bash"]
"""


def ensure_base_image(client: docker.DockerClient) -> None:
    try:
        client.images.get(BASE_IMAGE)
        logger.debug("Base image %s already exists", BASE_IMAGE)
        return
    except docker.errors.ImageNotFound:
        pass

    logger.info("Building base Docker image %s ...", BASE_IMAGE)
    dockerfile_bytes = DOCKERFILE.encode()
    fileobj = io.BytesIO(dockerfile_bytes)
    client.images.build(fileobj=fileobj, tag=BASE_IMAGE, rm=True)
    logger.info("Base image built successfully")
