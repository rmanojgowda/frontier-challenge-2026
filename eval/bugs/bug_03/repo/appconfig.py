"""Application configuration, read from the environment."""

import os


def get_worker_count():
    """Number of worker slots to spread jobs across.

    Falls back to a sensible default when ``APP_WORKERS`` is not set.
    """
    return int(os.environ.get("APP_WORKERS", "0"))


def get_batch_timeout():
    """Per-batch timeout in seconds (default 30)."""
    return int(os.environ.get("APP_BATCH_TIMEOUT", "30"))


def get_region():
    """Deployment region (default ``us-east-1``)."""
    return os.environ.get("APP_REGION", "us-east-1")


def partition(items):
    """Split ``items`` into roughly equal chunks, one per worker slot."""
    workers = get_worker_count()
    size = len(items) // workers
    return [items[i:i + size] for i in range(0, len(items), size)]
