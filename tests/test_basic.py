from __future__ import annotations

import pytest

from repocraft.config import RepoCraftConfig
from repocraft.evidence.collector import EvidenceCollector
from repocraft.evidence.models import EvidenceType, Phase


def test_config_parses_owner_repo():
    cfg = RepoCraftConfig(repo_url="https://github.com/psf/requests", issue_number=1)
    assert cfg.owner == "psf"
    assert cfg.repo == "requests"


def test_config_invalid_url():
    with pytest.raises(ValueError, match="Cannot parse"):
        RepoCraftConfig(repo_url="https://notgithub.com/foo", issue_number=1)


def test_evidence_collector_add_and_get():
    col = EvidenceCollector()
    col.add(Phase.REPRODUCE, EvidenceType.COMMAND_OUTPUT, "Test output", "exit 1")
    col.add(Phase.FIX, EvidenceType.FILE_CONTENT, "Fixed file", "def foo(): pass")

    assert len(col.get_by_phase(Phase.REPRODUCE)) == 1
    assert len(col.get_by_phase(Phase.FIX)) == 1
    assert len(col.get_all()) == 2


def test_evidence_summary_includes_title():
    col = EvidenceCollector()
    col.add(Phase.REPRODUCE, EvidenceType.ERROR_OUTPUT, "Stack trace", "AttributeError: foo")
    summary = col.get_summary_for_phase(Phase.REPRODUCE)
    assert "Stack trace" in summary
    assert "AttributeError" in summary


def test_evidence_summary_empty_phase():
    col = EvidenceCollector()
    summary = col.get_summary_for_phase(Phase.FIX)
    assert "No evidence" in summary


def test_parse_issue_url():
    from repocraft.cli import parse_issue_url
    owner, repo, num = parse_issue_url("https://github.com/psf/requests/issues/42")
    assert owner == "psf"
    assert repo == "requests"
    assert num == 42


def test_parse_issue_url_invalid():
    from repocraft.cli import parse_issue_url
    with pytest.raises(ValueError):
        parse_issue_url("https://github.com/psf/requests")
