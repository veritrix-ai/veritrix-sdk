"""Framework integrations for Veritrix."""

from veritrix.integrations.crewai import setup_crewai
from veritrix.integrations.langchain import setup_langchain

__all__ = ["setup_langchain", "setup_crewai"]
