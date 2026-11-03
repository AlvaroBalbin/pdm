from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from pdm import termui
from pdm.exceptions import CandidateNotFound, InstallationError
from pdm.installers.synchronizers import Synchronizer
from pdm.models.candidates import Candidate
from pdm.models.requirements import parse_requirement


@pytest.mark.parametrize("parallel", [False, True])
def test_missing_candidate_reports_reason_without_traceback(
    mocker: MockerFixture, capsys: pytest.CaptureFixture[str], parallel: bool
) -> None:
    """Issue #1639: expected installation failures should have readable output."""
    environment = mocker.Mock()
    environment.project.config = {"install.cache": False, "install.parallel": parallel}
    environment.project.core.ui = termui.UI(verbosity=termui.Verbosity.NORMAL)
    environment.get_working_set.return_value = {}
    environment.project.get_locked_repository.return_value.all_candidates = {}
    environment.get_paths.return_value = {}
    candidate = Candidate(parse_requirement("tensorflow"), name="tensorflow", version="2.11.0")
    mocker.patch.object(Candidate, "prepare")
    synchronizer = Synchronizer(
        environment, candidates={"tensorflow": candidate}, requirements=[candidate.req], retry_times=0
    )
    mocker.patch.object(synchronizer, "_fix_pth_files")
    reason = "No candidate is found for `tensorflow` that matches the environment or hashes"
    install = mocker.patch.object(synchronizer.manager, "install", side_effect=CandidateNotFound(reason))

    with pytest.raises(InstallationError, match="Some package operations failed"):
        synchronizer.synchronize()

    install.assert_called_once_with(candidate)
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "tensorflow" in output
    assert "matches the environment or hashes" in output
    assert "Traceback (most recent call last)" not in output, output
