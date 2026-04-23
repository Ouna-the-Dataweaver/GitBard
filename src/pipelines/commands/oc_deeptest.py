from .base import Command


class DeepTestCommand(Command):
    @property
    def name(self) -> str:
        return "oc_deeptest"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_deeptest"

    @property
    def preset(self) -> str:
        return "deep_test"

    @property
    def description(self) -> str:
        return "Runs preparation before the main OpenCode execution."

    @property
    def timeout_seconds(self) -> int:
        return 3600

    @property
    def enable_repo_hook(self) -> bool:
        return True

    @property
    def enable_opencode_preparation(self) -> bool:
        return True

    @property
    def allow_dependency_install(self) -> bool:
        return True
