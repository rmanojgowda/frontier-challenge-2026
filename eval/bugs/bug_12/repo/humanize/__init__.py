"""Minimal package shim for this fixture.

The upstream ``humanize`` package ``__init__`` imports ``pkg_resources``, loads
compiled locale catalogs, and pulls in sibling modules (``time``, ``filesize``)
that are unrelated to this bug. This fixture exposes only ``intword``; its
implementation in ``number.py`` (and the ``i18n`` helper it depends on) is the
verbatim historical source — see ``../../ground_truth.md`` for provenance.
"""

from .number import intword

__all__ = ["intword"]
