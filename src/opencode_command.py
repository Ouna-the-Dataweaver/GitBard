from __future__ import annotations

import os
import shlex

DEFAULT_OPENCODE_COMMAND = "opencode"


def opencode_command_args(*args: str) -> list[str]:
    command = os.getenv("OPENCODE_COMMAND", DEFAULT_OPENCODE_COMMAND).strip()
    base_args = shlex.split(command or DEFAULT_OPENCODE_COMMAND)
    return [*base_args, *args]
