import pytest
from src.pipelines.commands.oc_review import ReviewCommand
from src.pipelines.commands.oc_ask import AskCommand
from src.pipelines.commands.oc_test import TestCommand


def test_review_command():
    cmd = ReviewCommand()
    assert cmd.name == "oc_review"
    assert cmd.trigger_pattern == "/oc_review"
    pipeline = cmd.get_pipeline()
    assert pipeline.name == "oc_review"
    assert len(pipeline.stages) == 5


def test_ask_command():
    cmd = AskCommand()
    assert cmd.name == "oc_ask"
    assert cmd.trigger_pattern == "/oc_ask"
    pipeline = cmd.get_pipeline()
    assert pipeline.name == "oc_ask"
    assert len(pipeline.stages) == 5


def test_test_command():
    cmd = TestCommand()
    assert cmd.name == "oc_test"
    assert cmd.trigger_pattern == "/oc_test"
    pipeline = cmd.get_pipeline()
    assert pipeline.name == "oc_test"
    assert len(pipeline.stages) == 5
