import json
from pathlib import Path


def test_opencode_review_command_has_required_template_and_agent():
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "opencode.json"

    config = json.loads(config_path.read_text(encoding="utf-8"))

    review_command = config["command"]["oc_review"]
    assert isinstance(review_command["template"], str)
    assert review_command["template"].strip()
    assert review_command["agent"] == "gitlab-review"


def test_opencode_review_agent_uses_prompt_file():
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "opencode.json"

    config = json.loads(config_path.read_text(encoding="utf-8"))

    review_agent = config["agent"]["gitlab-review"]
    assert review_agent["prompt"] == "{file:./prompts/gitlab-review.md}"
    assert (repo_root / "prompts" / "gitlab-review.md").exists()


def test_opencode_prepare_agent_uses_prompt_file():
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "opencode.json"

    config = json.loads(config_path.read_text(encoding="utf-8"))

    prepare_agent = config["agent"]["gitlab-prepare"]
    assert prepare_agent["prompt"] == "{file:./prompts/gitlab-prepare.md}"
    assert (repo_root / "prompts" / "gitlab-prepare.md").exists()
