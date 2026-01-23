from typing import Optional, List
from .commands.base import Command
from .commands.oc_review import ReviewCommand
from .commands.oc_ask import AskCommand
from .commands.oc_test import TestCommand
from .base import Pipeline


COMMANDS: List[Command] = [ReviewCommand(), AskCommand(), TestCommand()]


def detect_command(text: str) -> Optional[Command]:
    """Detect command from text"""
    for command in COMMANDS:
        if command.trigger_pattern in text:
            return command
    return None


def get_pipeline_for_command(command_name: str) -> Optional[Pipeline]:
    """Get pipeline by command name"""
    for command in COMMANDS:
        if command.name == command_name:
            return command.get_pipeline()
    return None
