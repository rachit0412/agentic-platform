"""
A08:2025 - Software or Data Integrity Failures
Data Integrity Validation Module for FastAPI

Provides:
- Secure JSON deserialization
- Request/response integrity checks
- Cryptographic signing and verification
- Artifact hash validation
- Deployment verification
"""

import hashlib
import json
import hmac
import base64
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from functools import wraps
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


class IntegrityValidator:
    """Validates data and code integrity throughout the pipeline."""
    
    def __init__(self, secret_key: str):
        """Initialize with application secret key.
        
        Args:
            secret_key: Cryptographic key for signing
        """
        self.secret_key = secret_key.encode()
    
    def compute_hash(self, data: bytes | str, algorithm: str = "sha256") -> str:
        """Compute cryptographic hash of data.
        
        Args:
            data: Data to hash
            algorithm: Hash algorithm (sha256, sha512, sha1)
            
        Returns:
            Hex digest of hash
        """
        if isinstance(data, str):
            data = data.encode()
        
        if algorithm == "sha256":
            return hashlib.sha256(data).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(data).hexdigest()
        elif algorithm == "sha1":
            return hashlib.sha1(data).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def verify_hash(self, data: bytes | str, expected_hash: str, 
                   algorithm: str = "sha256") -> bool:
        """Verify data matches expected hash.
        
        Args:
            data: Data to verify
            expected_hash: Expected hash value
            algorithm: Hash algorithm
            
        Returns:
            True if hashes match, False otherwise
        """
        computed = self.compute_hash(data, algorithm)
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed, expected_hash)
    
    def sign_data(self, data: Dict[str, Any] | str) -> tuple[str, str]:
        """Sign data with HMAC-SHA256.
        
        Args:
            data: Data to sign (dict or string)
            
        Returns:
            Tuple of (base64_encoded_data, base64_encoded_signature)
        """
        if isinstance(data, dict):
            json_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        else:
            json_data = str(data)
        
        data_bytes = json_data.encode()
        signature = hmac.new(
            self.secret_key,
            data_bytes,
            hashlib.sha256
        ).digest()
        
        return (
            base64.b64encode(data_bytes).decode(),
            base64.b64encode(signature).decode()
        )
    
    def verify_signature(self, data: str, signature: str) -> bool:
        """Verify data signature using HMAC-SHA256.
        
        Args:
            data: Base64-encoded data
            signature: Base64-encoded signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            data_bytes = base64.b64decode(data.encode())
            sig_bytes = base64.b64decode(signature.encode())
            
            expected_sig = hmac.new(
                self.secret_key,
                data_bytes,
                hashlib.sha256
            ).digest()
            
            # Constant-time comparison
            return hmac.compare_digest(sig_bytes, expected_sig)
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


class SecureJSONDecoder:
    """Secure JSON deserialization preventing injection attacks."""
    
    @staticmethod
    def safe_loads(json_str: str, max_depth: int = 10) -> Dict[str, Any] | list | Any:
        """Safely deserialize JSON with depth limits.
        
        Args:
            json_str: JSON string to deserialize
            max_depth: Maximum nesting depth allowed
            
        Returns:
            Deserialized object
            
        Raises:
            ValueError: If JSON is invalid or depth exceeded
        """
        try:
            # Standard loads with depth validation
            obj = json.loads(json_str)
            
            # Validate depth
            if SecureJSONDecoder._check_depth(obj, max_depth) is False:
                raise ValueError(f"JSON depth exceeds maximum of {max_depth}")
            
            return obj
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            raise ValueError(f"Invalid JSON: {e}")
    
    @staticmethod
    def _check_depth(obj: Any, max_depth: int, current: int = 0) -> bool:
        """Recursively check JSON nesting depth."""
        if current > max_depth:
            return False
        
        if isinstance(obj, dict):
            return all(
                SecureJSONDecoder._check_depth(v, max_depth, current + 1)
                for v in obj.values()
            )
        elif isinstance(obj, list):
            return all(
                SecureJSONDecoder._check_depth(item, max_depth, current + 1)
                for item in obj
            )
        
        return True


class ArtifactVerifier:
    """Verifies integrity of deployment artifacts."""
    
    @staticmethod
    def generate_manifest(files: Dict[str, str]) -> Dict[str, Any]:
        """Generate manifest with file hashes.
        
        Args:
            files: Dict of {filepath: content}
            
        Returns:
            Manifest with metadata and hashes
        """
        hashes = {}
        for filepath, content in files.items():
            hashes[filepath] = hashlib.sha256(content.encode()).hexdigest()
        
        return {
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "files": hashes,
            "hash": hashlib.sha256(
                json.dumps(hashes, sort_keys=True).encode()
            ).hexdigest()
        }
    
    @staticmethod
    def verify_manifest(manifest: Dict[str, Any], files: Dict[str, str]) -> bool:
        """Verify files match manifest hashes.
        
        Args:
            manifest: Manifest dict with expected hashes
            files: Dict of {filepath: content}
            
        Returns:
            True if all files match, False otherwise
        """
        for filepath, content in files.items():
            if filepath not in manifest.get("files", {}):
                logger.warning(f"File not in manifest: {filepath}")
                return False
            
            expected_hash = manifest["files"][filepath]
            actual_hash = hashlib.sha256(content.encode()).hexdigest()
            
            if not hmac.compare_digest(expected_hash, actual_hash):
                logger.error(f"Hash mismatch for {filepath}")
                return False
        
        return True


class RequestIntegrityValidator:
    """Middleware for validating request/response integrity."""
    
    def __init__(self, validator: IntegrityValidator):
        """Initialize with integrity validator.
        
        Args:
            validator: IntegrityValidator instance
        """
        self.validator = validator
    
    async def validate_request_signature(self, request: Request) -> bool:
        """Validate request has valid signature.
        
        Expects headers:
            X-Payload-Signature: base64-encoded HMAC-SHA256
            X-Payload-Hash: sha256 hash of body
            
        Args:
            request: FastAPI request object
            
        Returns:
            True if signature valid, False otherwise
        """
        body = await request.body()
        
        signature = request.headers.get("X-Payload-Signature")
        payload_hash = request.headers.get("X-Payload-Hash")
        
        if not signature or not payload_hash:
            logger.warning("Missing signature headers")
            return False
        
        # Verify payload hash
        computed_hash = hashlib.sha256(body).hexdigest()
        if not hmac.compare_digest(computed_hash, payload_hash):
            logger.error("Payload hash mismatch")
            return False
        
        # Verify signature
        try:
            data_b64 = base64.b64encode(body).decode()
            return self.validator.verify_signature(data_b64, signature)
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


# ──────────────────────────────────────────────────────────────────────────
# Decorators for Route Protection
# ──────────────────────────────────────────────────────────────────────────

def require_signature_validation(validator: IntegrityValidator):
    """Decorator to require request signature validation.
    
    Usage:
        @app.post("/secure-endpoint")
        @require_signature_validation(integrity_validator)
        async def secure_endpoint(request: Request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            req_validator = RequestIntegrityValidator(validator)
            if not await req_validator.validate_request_signature(request):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid request signature"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def verify_artifact_integrity(validator: IntegrityValidator):
    """Decorator to verify artifact/package integrity.
    
    Expects request body with:
        {
            "manifest": {...},
            "files": {...}
        }
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                body = await request.json()
                manifest = body.get("manifest")
                files = body.get("files")
                
                if not manifest or not files:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing manifest or files"
                    )
                
                if not ArtifactVerifier.verify_manifest(manifest, files):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Artifact integrity verification failed"
                    )
                
                # Continue with the handler
                return await func(request, *args, **kwargs)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON"
                )
        return wrapper
    return decorator


# ──────────────────────────────────────────────────────────────────────────
# Configuration & Initialization
# ──────────────────────────────────────────────────────────────────────────

def create_integrity_validator(secret_key: str) -> IntegrityValidator:
    """Factory function to create configured validator.
    
    Args:
        secret_key: Secret key for signing operations
        
    Returns:
        Configured IntegrityValidator instance
    """
    if not secret_key or len(secret_key) < 32:
        logger.warning("Secret key should be at least 32 characters")
    
    return IntegrityValidator(secret_key)


# Export public API
__all__ = [
    'IntegrityValidator',
    'SecureJSONDecoder',
    'ArtifactVerifier',
    'RequestIntegrityValidator',
    'require_signature_validation',
    'verify_artifact_integrity',
    'create_integrity_validator',
]
