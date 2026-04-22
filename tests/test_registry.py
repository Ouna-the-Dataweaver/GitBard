from src.pipelines.registry import contains_user_mention, detect_command


def test_detect_command_returns_matching_command():
    command = detect_command("please run /oc_review on this change")

    assert command is not None
    assert command.name == "oc_review"


def test_detect_command_returns_deeptest_command():
    command = detect_command("please run /oc_deeptest on this change")

    assert command is not None
    assert command.name == "oc_deeptest"


def test_contains_user_mention_matches_exact_username():
    assert contains_user_mention("please check this @nid-bugbard", "nid-bugbard")
    assert not contains_user_mention("@nid-bugbard-extra should not match", "nid-bugbard")
    assert not contains_user_mention("plain text only", "nid-bugbard")
