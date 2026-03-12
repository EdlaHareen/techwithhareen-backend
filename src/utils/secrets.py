"""
GCP Secret Manager helper — fetches secret values at runtime.

In production, secrets are injected as env vars via Cloud Run's
--set-secrets flag. This module is a fallback for fetching
secrets programmatically if needed (e.g., rotation scenarios).
"""

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def get_secret(secret_id: str, version: str = "latest") -> str:
    """
    Fetch a secret from GCP Secret Manager.
    Results are cached — do not use for frequently-rotated secrets.

    Falls back to environment variables for local development.
    """
    # In local dev, read from environment
    env_key = secret_id.upper().replace("-", "_")
    env_val = os.environ.get(env_key)
    if env_val:
        return env_val

    # In production, use Secret Manager SDK
    try:
        from google.cloud import secretmanager

        project_id = os.environ["GCP_PROJECT_ID"]
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        value = response.payload.data.decode("utf-8").strip()
        logger.debug(f"Fetched secret: {secret_id}")
        return value

    except Exception as e:
        logger.error(f"Failed to fetch secret '{secret_id}': {e}")
        raise RuntimeError(f"Secret '{secret_id}' not available") from e
