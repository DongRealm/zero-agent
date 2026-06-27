"""Verify Phase D agent dependencies are installed."""

import importlib


def test_deepagents_importable() -> None:
    module = importlib.import_module("deepagents")
    assert module is not None


def test_langchain_openai_importable() -> None:
    module = importlib.import_module("langchain_openai")
    assert module is not None
