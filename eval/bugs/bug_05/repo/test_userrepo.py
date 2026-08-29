import pytest

from userrepo import UserRepo


@pytest.fixture
def repo():
    r = UserRepo()
    r.add_user(1, "Alice")
    r.add_user(2, "Bob")
    return r


def test_get_user_returns_record(repo):
    assert repo.get_user(1) == {"id": 1, "name": "Alice"}


def test_get_unknown_user_is_none(repo):
    assert repo.get_user(99) is None


def test_update_then_get_returns_new_name(repo):
    repo.get_user(1)                     # warm the cache
    repo.update_name(1, "Alicia")
    assert repo.get_user(1) == {"id": 1, "name": "Alicia"}


def test_update_without_prior_read(repo):
    repo.update_name(2, "Bobby")
    assert repo.get_user(2) == {"id": 2, "name": "Bobby"}


def test_delete_evicts_cache(repo):
    repo.get_user(1)
    repo.delete_user(1)
    assert repo.get_user(1) is None
