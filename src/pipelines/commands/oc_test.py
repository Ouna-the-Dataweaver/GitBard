from .base import Command


class TestCommand(Command):
    @property
    def name(self) -> str:
        return "oc_test"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_test"

    @property
    def description(self) -> str:
        return "Uses the same real opencode CLI path for ad hoc testing."
