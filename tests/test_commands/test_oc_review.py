from src.pipelines.commands.oc_review import ReviewCommand
from src.pipelines.commands.oc_ask import AskCommand
from src.pipelines.commands.oc_deepreview import DeepReviewCommand
from src.pipelines.stages.context_builder import WorkspaceAcquisitionStage
from src.pipelines.stages.issue_context_fetcher import IssueContextFetcherStage
from src.pipelines.stages.opencode_integration import OpencodeIntegrationStage
from src.pipelines.stages.workspace_preparation import WorkspacePreparationStage


def test_review_command():
    cmd = ReviewCommand()
    assert cmd.name == "oc_review"
    assert cmd.trigger_pattern == "/oc_review"
    assert cmd.agent_name == "gitlab-review"
    pipeline = cmd.get_pipeline()
    assert pipeline.name == "oc_review"
    assert len(pipeline.stages) == 6
    assert isinstance(pipeline.stages[2], WorkspaceAcquisitionStage)
    assert isinstance(pipeline.stages[3], IssueContextFetcherStage)
    assert isinstance(pipeline.stages[4], OpencodeIntegrationStage)


def test_ask_command():
    cmd = AskCommand()
    assert cmd.name == "oc_ask"
    assert cmd.trigger_pattern == "/oc_ask"
    assert cmd.agent_name == "Build"
    pipeline = cmd.get_pipeline()
    assert pipeline.name == "oc_ask"
    assert len(pipeline.stages) == 6
    assert isinstance(pipeline.stages[2], WorkspaceAcquisitionStage)
    assert isinstance(pipeline.stages[3], IssueContextFetcherStage)
    assert isinstance(pipeline.stages[4], OpencodeIntegrationStage)


def test_deepreview_command():
    cmd = DeepReviewCommand()
    assert cmd.name == "oc_deepreview"
    assert cmd.trigger_pattern == "/oc_deepreview"
    assert cmd.preset == "deep_review"
    assert cmd.agent_name == "deep_review"
    pipeline = cmd.get_pipeline()
    assert pipeline.name == "oc_deepreview"
    assert len(pipeline.stages) == 7
    assert isinstance(pipeline.stages[2], WorkspaceAcquisitionStage)
    assert isinstance(pipeline.stages[3], IssueContextFetcherStage)
    assert isinstance(pipeline.stages[4], WorkspacePreparationStage)
    assert pipeline.stages[4].preparation_config.routes == ("repo_hook", "opencode")
    assert isinstance(pipeline.stages[5], OpencodeIntegrationStage)
