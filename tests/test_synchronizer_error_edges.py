"""AI-assisted preservation controls for synchronizer error reporting."""

from __future__ import annotations

import pytest

from pdm import termui
from pdm.exceptions import BuildError, InstallationError
from pdm.installers.synchronizers import Synchronizer
from pdm.models.candidates import Candidate
from pdm.models.requirements import parse_requirement


def make_synchronizer(mocker, tmp_path, parallel, retry_times=0):
    environment = mocker.Mock()
    environment.project.config = {"install.cache": False, "install.parallel": parallel}
    environment.project.core.ui = termui.UI(verbosity=termui.Verbosity.NORMAL)
    environment.get_working_set.return_value = {}
    environment.project.get_locked_repository.return_value.all_candidates = {}
    environment.get_paths.return_value = {"purelib": str(tmp_path), "platlib": str(tmp_path)}
    candidate = Candidate(parse_requirement("demo"), name="demo", version="1.0")
    mocker.patch.object(Candidate, "prepare")
    synchronizer = Synchronizer(
        environment, candidates={"demo": candidate}, requirements=[candidate.req], retry_times=retry_times
    )
    return synchronizer, candidate


@pytest.mark.parametrize("parallel", [False, True])
@pytest.mark.parametrize("chain", ["explicit", "implicit", "suppressed"])
def test_chained_failure_retains_actionable_cause(mocker, tmp_path, capsys, parallel, chain):
    synchronizer, candidate = make_synchronizer(mocker, tmp_path, parallel)
    reason = "Missing compiler: compilateur-é\nSet CC to an available compiler"

    def install(can):
        assert can is candidate
        try:
            raise OSError(reason)
        except OSError as error:
            if chain == "explicit":
                raise BuildError("Wheel build failed") from error
            if chain == "suppressed":
                raise BuildError("Wheel build failed") from None
            raise BuildError("Wheel build failed")

    mocker.patch.object(synchronizer.manager, "install", side_effect=install)

    with pytest.raises(InstallationError, match="Some package operations failed"):
        synchronizer.synchronize()

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "add demo failed:" in output
    assert "Wheel build failed" in output
    if chain == "suppressed":
        assert "Missing compiler" not in output
        assert "Set CC" not in output
    else:
        assert "Missing compiler: compilateur-é" in output
        assert "Set CC to an available compiler" in output


@pytest.mark.parametrize("parallel", [False, True])
def test_successful_retry_clears_previous_error_summary(mocker, tmp_path, capsys, parallel):
    synchronizer, candidate = make_synchronizer(mocker, tmp_path, parallel, retry_times=1)
    install = mocker.patch.object(
        synchronizer.manager, "install", side_effect=[BuildError("Temporary build failure"), None]
    )
    pending = tmp_path / "demo.pth.pdmtmp"
    pending.write_text("demo\n", encoding="utf-8")

    assert synchronizer.synchronize() is None

    assert install.call_args_list == [mocker.call(candidate), mocker.call(candidate)]
    assert not pending.exists()
    assert (tmp_path / "demo.pth").read_text(encoding="utf-8") == "demo\n"
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "ERRORS:" not in output
    assert "Temporary build failure" not in output
