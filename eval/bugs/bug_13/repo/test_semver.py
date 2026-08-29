import pytest

from semver import compare


def test_numeric_prerelease_identifier_sorts_below_text():
    # SemVer precedence rule 11: a numeric pre-release identifier has LOWER
    # precedence than an alphanumeric one. So with a shared "alpha" prefix,
    # "alpha.1" must sort before "alpha.beta".
    assert compare("1.0.0-alpha.1", "1.0.0-alpha.beta") == -1
    assert compare("1.0.0-alpha.beta", "1.0.0-alpha.1") == 1


def test_numeric_prerelease_identifier_sorts_below_text_first_field():
    # Same rule at the first identifier: "1.0.0-1" < "1.0.0-alpha".
    assert compare("1.0.0-1", "1.0.0-alpha") == -1
    assert compare("1.0.0-alpha", "1.0.0-1") == 1


def test_numeric_identifiers_compare_numerically():
    # Already correct at this revision -- must not regress.
    assert compare("1.0.0-beta.2", "1.0.0-beta.11") == -1


def test_any_prerelease_sorts_below_the_release():
    # Already correct -- must not regress.
    assert compare("1.0.0-rc.1", "1.0.0") == -1


def test_shorter_prerelease_sorts_below_its_longer_prefix():
    # Already correct (field-count / prefix rule) -- must not regress.
    assert compare("1.0.0-alpha", "1.0.0-alpha.1") == -1


def test_semver_org_precedence_chain():
    chain = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]
    for lo, hi in zip(chain, chain[1:]):
        assert compare(lo, hi) == -1
        assert compare(hi, lo) == 1
