from policy_agent.cli import main

VALID = """
policy: job-naming
resource_type: job
effect: allow
rule: { attribute: name, operator: matches_regex, value: "^prod_.+$" }
"""

INVALID_ATTRIBUTE = """
policy: broken
resource_type: job
effect: deny
rule: { attribute: not_a_real_attribute, operator: equals, value: x }
"""


def test_validate_returns_zero_for_valid_files(tmp_path, capsys):
    (tmp_path / "good.yaml").write_text(VALID)
    exit_code = main(["validate", str(tmp_path)])
    assert exit_code == 0
    assert "OK" in capsys.readouterr().out


def test_validate_returns_one_and_reports_invalid_files(tmp_path, capsys):
    (tmp_path / "bad.yaml").write_text(INVALID_ATTRIBUTE)
    exit_code = main(["validate", str(tmp_path)])
    assert exit_code == 1
    assert "ERR" in capsys.readouterr().out


def test_validate_accepts_explicit_file_paths(tmp_path, capsys):
    good = tmp_path / "good.yaml"
    good.write_text(VALID)
    assert main(["validate", str(good)]) == 0
    assert "1 policy(ies)" in capsys.readouterr().out
