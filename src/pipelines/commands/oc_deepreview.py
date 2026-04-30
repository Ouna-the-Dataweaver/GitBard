from .base import Command


class DeepReviewCommand(Command):
    @property
    def name(self) -> str:
        return "oc_deepreview"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_deepreview"

    @property
    def preset(self) -> str:
        return "deep_review"

    @property
    def description(self) -> str:
        return "Runs repository preparation before the deep review agent."

    @property
    def agent_name(self) -> str:
        return "deep_review"

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
