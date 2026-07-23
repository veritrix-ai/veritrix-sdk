from __future__ import annotations

from unittest.mock import patch

from veritrix.integrations.crewai import setup_crewai
from veritrix.integrations.langchain import setup_langchain


def test_setup_langchain_skips_without_dependency() -> None:
    with patch.dict("sys.modules", {"langchain_core": None}):
        setup_langchain()


def test_setup_crewai_skips_without_dependency() -> None:
    with patch.dict("sys.modules", {"crewai": None}):
        setup_crewai()


def test_setup_crewai_skips_when_import_raises() -> None:
    def _raise_permission_error() -> None:
        raise PermissionError("cannot create storage directory")

    with patch("builtins.__import__", side_effect=_raise_permission_error):
        setup_crewai()
