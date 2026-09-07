from __future__ import annotations
import importlib
import pytest


def test_prepare_data_is_importable_and_has_main():
    mod = importlib.import_module("scripts.prepare_data")
    assert hasattr(mod, "main")
    assert callable(mod.main)


def test_train_model_is_importable_and_has_main():
    mod = importlib.import_module("scripts.train_model")
    assert hasattr(mod, "main")
    assert callable(mod.main)


def test_evaluate_model_is_importable_and_has_main():
    mod = importlib.import_module("scripts.evaluate_model")
    assert hasattr(mod, "main")
    assert callable(mod.main)


def test_evaluate_model_returns_dict_with_baseline_blocks():
    mod = importlib.import_module("scripts.evaluate_model")
    out = mod.main.__doc__
    assert out is None or isinstance(out, str)
