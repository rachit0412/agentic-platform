"""
Docker Image Security & Version Management

Provides functionality for:
- Tracking Docker image versions
- Scanning for vulnerabilities  
- Managing version updates
- Monthly security reminders
"""

import json
import logging
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("agent-service.image-manager")


@dataclass
class ImageInfo:
    """Docker image version and security information."""
    name: str
    registry: str
    current_version: str
    latest_version: Optional[str] = None
    security_status: str = "unknown"  # unknown, safe, warning, critical
    vulnerabilities: list[dict] = field(default_factory=list)
    last_checked: Optional[str] = None
    env_var: Optional[str] = None

    def to_dict(self):
        return asdict(self)


# Default images managed by platform with current versions from docker-compose.yml
MANAGED_IMAGES = {
    "n8n": {
        "registry": "n8nio/n8n",
        "current_version": os.getenv("N8N_IMAGE_TAG", "2.37.4-dacee6c-arm64"),
        "env_var": "N8N_IMAGE_TAG",
    },
    "nginx": {
        "registry": "nginx",
        "current_version": os.getenv("NGINX_IMAGE_TAG", "1.27.0-alpine"),
        "env_var": "NGINX_IMAGE_TAG",
    },
    "ollama": {
        "registry": "ollama/ollama",
        "current_version": os.getenv("OLLAMA_IMAGE_TAG", "0.4.2"),
        "env_var": "OLLAMA_IMAGE_TAG",
    },
    "prometheus": {
        "registry": "prom/prometheus",
        "current_version": os.getenv("PROMETHEUS_IMAGE_TAG", "2.50.1"),
        "env_var": "PROMETHEUS_IMAGE_TAG",
    },
    "langfuse": {
        "registry": "langfuse/langfuse",
        "current_version": os.getenv("LANGFUSE_IMAGE_TAG", "2.185.0"),
        "env_var": "LANGFUSE_IMAGE_TAG",
    },
    "python": {
        "registry": "python",
        "current_version": "3.11.9-slim",
        "latest_version": "3.11.10-slim",
    },
    "node": {
        "registry": "node",
        "current_version": "20.11.1-alpine",
        "latest_version": "20.12.2-alpine",
    },
    "postgres": {
        "registry": "postgres",
        "current_version": "16-alpine",
        "latest_version": "16.4-alpine",
    },
    "grafana": {
        "registry": "grafana/grafana",
        "current_version": "11.0.0",
    },
    "loki": {
        "registry": "grafana/loki",
        "current_version": "3.0.0",
    },
    "chromadb": {
        "registry": "chromadb/chroma",
        "current_version": "0.6.3",
    },
    "otel": {
        "registry": "otel/opentelemetry-collector-contrib",
        "current_version": "0.100.0",
    },
}

# Known vulnerabilities mapping (simplified for demo)
KNOWN_VULNERABILITIES = {
    "nginx:1.27.0-alpine": {
        "vulnerabilities": [
            {
                "id": "CVE-2024-XXXXX",
                "severity": "medium",
                "description": "Update available for improved security",
                "fixed_in": "1.27.1-alpine",
            }
        ],
        "status": "warning",
    },
    "python:3.11.9-slim": {
        "vulnerabilities": [
            {
                "id": "CVE-2024-YYYYY",
                "severity": "low",
                "description": "HTTP/2 CONTINUATION flood mitigation",
                "fixed_in": "3.11.10-slim",
            }
        ],
        "status": "warning",
    },
}


class DockerImageManager:
    """Manages Docker image versions, updates, and security scanning."""

    def __init__(self):
        self.images = {}
        self._initialize_images()
        self.last_reminder_check = None
        self.reminder_interval = timedelta(days=30)
        self.env_file = os.getenv("ENV_FILE", "/app/.env")

    def _initialize_images(self):
        """Initialize all managed images."""
        for name, config in MANAGED_IMAGES.items():
            self.images[name] = ImageInfo(
                name=name,
                registry=config["registry"],
                current_version=config["current_version"],
                latest_version=config.get("latest_version"),
                env_var=config.get("env_var"),
            )

    def get_all_images(self) -> dict[str, ImageInfo]:
        """Get all managed images."""
        return self.images

    def get_image_info(self, image_name: str) -> Optional[ImageInfo]:
        """Get info for a specific image."""
        return self.images.get(image_name)

    def scan_image_for_vulnerabilities(self, image_name: str) -> dict:
        """
        Scan an image for known vulnerabilities.
        Returns security status and list of vulnerabilities.
        """
        image = self.images.get(image_name)
        if not image:
            return {"error": "Image not found"}

        full_image_tag = f"{image.registry}:{image.current_version}"

        # Check against known vulnerabilities
        vuln_data = KNOWN_VULNERABILITIES.get(full_image_tag, {})
        vulnerabilities = vuln_data.get("vulnerabilities", [])
        status = vuln_data.get("status", "safe")

        # If no known vulnerabilities, mark as safe
        if not vulnerabilities:
            status = "safe"

        image.security_status = status
        image.vulnerabilities = vulnerabilities
        image.last_checked = datetime.now().isoformat()

        return {
            "image": full_image_tag,
            "status": status,
            "vulnerability_count": len(vulnerabilities),
            "vulnerabilities": vulnerabilities,
            "last_checked": image.last_checked,
        }

    def scan_all_images(self) -> dict:
        """Scan all images for vulnerabilities."""
        results = {
            "total": len(self.images),
            "safe": 0,
            "warning": 0,
            "critical": 0,
            "scanned_at": datetime.now().isoformat(),
            "images": {},
        }

        for name, image in self.images.items():
            scan_result = self.scan_image_for_vulnerabilities(name)
            if "error" not in scan_result:
                status = scan_result["status"]
                results["images"][name] = scan_result
                if status == "safe":
                    results["safe"] += 1
                elif status == "warning":
                    results["warning"] += 1
                elif status == "critical":
                    results["critical"] += 1

        return results

    def check_for_updates(self, image_name: str) -> dict:
        """Check if an image has newer version available."""
        image = self.images.get(image_name)
        if not image:
            return {"error": "Image not found"}

        if not image.latest_version:
            return {
                "image": image_name,
                "current": image.current_version,
                "latest": None,
                "update_available": False,
            }

        update_available = image.latest_version != image.current_version

        return {
            "image": image_name,
            "current": image.current_version,
            "latest": image.latest_version,
            "update_available": update_available,
        }

    def check_all_for_updates(self) -> dict:
        """Check all images for available updates."""
        results = {
            "checked_at": datetime.now().isoformat(),
            "updates_available": 0,
            "images": {},
        }

        for name in self.images:
            check = self.check_for_updates(name)
            if "error" not in check:
                results["images"][name] = check
                if check.get("update_available"):
                    results["updates_available"] += 1

        return results

    def get_security_summary(self) -> dict:
        """Get overall security summary of all images."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_images": len(self.images),
            "security_status": {"safe": 0, "warning": 0, "critical": 0},
            "total_vulnerabilities": 0,
            "needs_immediate_attention": [],
            "recommended_updates": [],
        }

        for name, image in self.images.items():
            if image.security_status == "safe":
                summary["security_status"]["safe"] += 1
            elif image.security_status == "warning":
                summary["security_status"]["warning"] += 1
                summary["needs_immediate_attention"].append(name)
            elif image.security_status == "critical":
                summary["security_status"]["critical"] += 1
                summary["needs_immediate_attention"].append(name)

            summary["total_vulnerabilities"] += len(image.vulnerabilities)

            # Check for updates
            if image.latest_version and image.latest_version != image.current_version:
                summary["recommended_updates"].append(
                    {
                        "image": name,
                        "current": image.current_version,
                        "latest": image.latest_version,
                        "env_var": image.env_var,
                    }
                )

        return summary

    def update_image_version(self, image_name: str, new_version: str) -> dict:
        """Update image version in environment."""
        image = self.images.get(image_name)
        if not image or not image.env_var:
            return {"error": "Image not found or not configurable"}

        try:
            old_version = image.current_version
            image.current_version = new_version

            # Update .env file if it exists
            if os.path.exists(self.env_file):
                self._update_env_file(image.env_var, new_version)

            logger.info(f"Updated {image_name} from {old_version} to {new_version}")

            return {
                "success": True,
                "image": image_name,
                "old_version": old_version,
                "new_version": new_version,
                "env_var": image.env_var,
                "next_steps": [
                    "Update docker-compose.yml environment",
                    "Run: docker compose build --no-cache",
                    "Run: docker compose up -d",
                ],
            }
        except Exception as e:
            logger.error(f"Failed to update {image_name}: {e}")
            return {"error": str(e)}

    def _update_env_file(self, env_var: str, value: str):
        """Update environment variable in .env file."""
        if not os.path.exists(self.env_file):
            with open(self.env_file, "w") as f:
                f.write(f"{env_var}={value}\n")
            return

        with open(self.env_file, "r") as f:
            lines = f.readlines()

        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{env_var}="):
                lines[i] = f"{env_var}={value}\n"
                updated = True
                break

        if not updated:
            lines.append(f"{env_var}={value}\n")

        with open(self.env_file, "w") as f:
            f.writelines(lines)

    def get_environment_variables(self) -> dict:
        """Get all image-related environment variables."""
        env_vars = {}
        for name, image in self.images.items():
            if image.env_var:
                env_vars[image.env_var] = image.current_version
        return env_vars

    def get_available_versions(self, image_name: str) -> list[str]:
        """Get available versions for a Docker image.
        
        Comprehensive version map for all supported images.
        Falls back gracefully for unknown images.
        """
        # Comprehensive version mapping
        version_map = {
            # Development bases
            'python': ['3.12.4', '3.12.3', '3.12.2', '3.11.10', '3.11.9'],
            'node': ['22.1.0', '22.0.0', '20.15.1', '20.14.0', '20.13.0'],
            
            # Orchestration & Workflow
            'n8n': ['2.37.4', '2.37.3', '2.37.2', '2.36.5', '2.36.4'],
            'n8n_image_tag': ['2.37.4', '2.37.3', '2.37.2', '2.36.5', '2.36.4'],
            
            # Data & Storage
            'postgres': ['17.0', '16.3', '16.2', '15.7', '15.6'],
            'postgresql': ['17.0', '16.3', '16.2', '15.7', '15.6'],
            'redis': ['7.2.4', '7.2.3', '7.2.2', '7.0.15', '7.0.14'],
            'chromadb': ['0.4.24', '0.4.23', '0.4.22', '0.4.21', '0.4.20'],
            
            # ML/LLM
            'ollama': ['0.3.10', '0.3.9', '0.3.8', '0.3.7', '0.3.6'],
            
            # Platform services
            'datastore': ['latest', 'v1.0.0', 'v0.9.9', 'v0.9.8', 'v0.9.7'],
            'datastore_db': ['latest', 'v1.0.0', 'v0.9.9', 'v0.9.8', 'v0.9.7'],
            'tools': ['latest', 'v1.0.0', 'v0.9.9', 'v0.9.8', 'v0.9.7'],
            'tools_service': ['latest', 'v1.0.0', 'v0.9.9', 'v0.9.8', 'v0.9.7'],
            'agent': ['latest', 'v1.0.0', 'v0.9.9', 'v0.9.8', 'v0.9.7'],
            'agent_service': ['latest', 'v1.0.0', 'v0.9.9', 'v0.9.8', 'v0.9.7'],
            
            # Observability
            'prometheus': ['v2.53.0', 'v2.52.0', 'v2.51.2', 'v2.51.1', 'v2.51.0'],
            'grafana': ['11.0.0', '10.4.1', '10.4.0', '10.3.3', '10.3.2'],
            'loki': ['3.0.0', '2.9.7', '2.9.6', '2.9.5', '2.9.4'],
            
            # Message queue
            'rabbitmq': ['3.13.0', '3.12.13', '3.12.12', '3.11.28', '3.11.27'],
            
            # Utilities
            'nginx': ['1.27.0', '1.26.2', '1.26.1', '1.26.0', '1.25.5'],
        }
        
        # Normalize the image name (handle _image_tag, _image, etc. suffixes)
        normalized_name = image_name.lower()
        normalized_name = normalized_name.replace('_image_tag', '').replace('_image', '').replace('_service', '').replace('_db', '')
        
        # First try exact match
        if image_name.lower() in version_map:
            return version_map[image_name.lower()]
        
        # Then try normalized match
        if normalized_name in version_map:
            return version_map[normalized_name]
        
        # Return empty list - frontend will show "no versions found" instead of generic fallback
        return []

    def should_show_security_reminder(self) -> bool:
        """Check if monthly security reminder should be shown."""
        if self.last_reminder_check is None:
            self.last_reminder_check = datetime.now()
            return True

        elapsed = datetime.now() - self.last_reminder_check
        if elapsed > self.reminder_interval:
            self.last_reminder_check = datetime.now()
            return True

        return False

    def get_all_images_as_dicts(self) -> list[dict]:
        """Get all images as dictionaries for JSON serialization."""
        return [img.to_dict() for img in self.images.values()]


# Global instance
_manager_instance = None


def get_image_manager() -> DockerImageManager:
    """Get or create the global image manager."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = DockerImageManager()
    return _manager_instance
