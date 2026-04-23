from .base import Command


class ReviewCommand(Command):
    @property
    def name(self) -> str:
        return "oc_review"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_review"

    @property
    def description(self) -> str:
        return "Runs the review agent when a merge request note requests review."

    @property
    def agent_name(self) -> str:
        return "gitlab-review"
