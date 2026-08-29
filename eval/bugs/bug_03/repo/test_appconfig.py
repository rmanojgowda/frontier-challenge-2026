import pytest

import appconfig
from appconfig import (
    get_worker_count,
    get_batch_timeout,
    get_region,
    partition,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("APP_WORKERS", "APP_BATCH_TIMEOUT", "APP_REGION"):
        monkeypatch.delenv(name, raising=False)


def test_worker_count_default_is_four():
    assert get_worker_count() == 4


def test_worker_count_reads_env(monkeypatch):
    monkeypatch.setenv("APP_WORKERS", "8")
    assert get_worker_count() == 8


def test_batch_timeout_default():
    assert get_batch_timeout() == 30


def test_region_default():
    assert get_region() == "us-east-1"


def test_partition_with_default_config():
    items = list(range(10))
    chunks = partition(items)
    assert sum(len(c) for c in chunks) == 10
    assert all(chunks)
