from .base import Command


class AskCommand(Command):
    @property
    def name(self) -> str:
        return "oc_ask"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_ask"

    @property
    def description(self) -> str:
        return "Runs the opencode CLI and posts its response back to the thread."
