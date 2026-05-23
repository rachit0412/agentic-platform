"""
Docker manager for provisioning managed MCP server containers.

Uses the Docker SDK to create, start, stop, restart, and remove containers
on the platform-net network. Each managed MCP server gets its own container
running the managed-mcp-base image with config injected via MCP_CONFIG env var.
"""

import json
import logging
import os
import re
import time

import httpx

logger = logging.getLogger("agent-service.docker-manager")

PLATFORM_NETWORK = os.environ.get("MANAGED_MCP_NETWORK", "agentic-platform_platform-net")
MANAGED_MCP_IMAGE = "managed-mcp-base:latest"
CONTAINER_PORT = 8080
CONTAINER_PREFIX = "managed-mcp-"
BUILD_CONTEXT_PATH = os.environ.get("MANAGED_MCP_BUILD_PATH", "/managed-mcp-base")


def get_docker_client():
    import docker

    host = os.environ.get("DOCKER_HOST", "")
    if host:
        return docker.DockerClient(base_url=host)
    return docker.DockerClient.from_env()


def build_base_image(client=None) -> str:
    if client is None:
        client = get_docker_client()
    logger.info("Building managed-mcp-base image from %s", BUILD_CONTEXT_PATH)
    image, logs = client.images.build(
        path=BUILD_CONTEXT_PATH,
        tag=MANAGED_MCP_IMAGE,
        rm=True,
    )
    for chunk in logs:
        if "stream" in chunk:
            logger.debug(chunk["stream"].strip())
    logger.info("Built image: %s", image.tags)
    return MANAGED_MCP_IMAGE


def _ensure_image(client):
    try:
        client.images.get(MANAGED_MCP_IMAGE)
    except Exception:
        build_base_image(client)


def create_managed_container(
    server_id: str,
    server_name: str,
    config: dict,
) -> dict:
    client = get_docker_client()
    _ensure_image(client)

    container_name = f"{CONTAINER_PREFIX}{server_id}"
    container_name = re.sub(r"[^a-zA-Z0-9_.-]", "-", container_name)

    # Remove any existing container with same name
    try:
        old = client.containers.get(container_name)
        old.remove(force=True)
    except Exception:
        pass

    container = client.containers.run(
        image=MANAGED_MCP_IMAGE,
        name=container_name,
        environment={"MCP_CONFIG": json.dumps(config)},
        network=PLATFORM_NETWORK,
        detach=True,
        labels={
            "managed-by": "agentic-platform",
            "mcp-server-id": server_id,
            "mcp-server-name": server_name,
        },
    )

    url = f"http://{container_name}:{CONTAINER_PORT}"

    return {
        "container_id": container.id,
        "container_name": container_name,
        "url": url,
    }


def stop_container(container_id: str) -> bool:
    client = get_docker_client()
    try:
        c = client.containers.get(container_id)
        c.stop(timeout=10)
        return True
    except Exception as e:
        logger.warning("Failed to stop container %s: %s", container_id, e)
        return False


def start_container(container_id: str) -> bool:
    client = get_docker_client()
    try:
        c = client.containers.get(container_id)
        c.start()
        return True
    except Exception as e:
        logger.warning("Failed to start container %s: %s", container_id, e)
        return False


def restart_container(container_id: str) -> bool:
    client = get_docker_client()
    try:
        c = client.containers.get(container_id)
        c.restart(timeout=10)
        return True
    except Exception as e:
        logger.warning("Failed to restart container %s: %s", container_id, e)
        return False


def remove_container(container_id: str) -> bool:
    client = get_docker_client()
    try:
        c = client.containers.get(container_id)
        c.remove(force=True)
        return True
    except Exception as e:
        logger.warning("Failed to remove container %s: %s", container_id, e)
        return False


def get_container_logs(container_id: str, tail: int = 100) -> str:
    client = get_docker_client()
    try:
        c = client.containers.get(container_id)
        return c.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error fetching logs: {e}"


def get_container_status(container_id: str) -> str:
    client = get_docker_client()
    try:
        c = client.containers.get(container_id)
        return c.status
    except Exception:
        return "not_found"


async def wait_for_health(url: str, timeout: int = 30) -> bool:
    health_url = url.rstrip("/") + "/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(health_url)
                if resp.status_code == 200:
                    return True
        except Exception:
            pass
        await _async_sleep(2)
    return False


async def _async_sleep(seconds: float):
    import asyncio

    await asyncio.sleep(seconds)
