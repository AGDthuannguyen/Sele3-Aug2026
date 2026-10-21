"""Focused checks for reusable steps and one report directory per pytest run."""

import json
import sys
from subprocess import TimeoutExpired
from time import monotonic, sleep
from xml.etree import ElementTree

import pytest

from pylenium.reporting import StepRecorder, install_recorder, record_step, reset_recorder, step


pytest_plugins = ["pytester"]


def test_step_decorator_nests_actions_without_changing_results():
    recorder = StepRecorder()
    token = install_recorder(recorder)

    @step("Submit login form")
    def submit():
        with record_step("Fill email"):
            return "sent"

    try:
        assert submit() == "sent"
    finally:
        reset_recorder(token)

    assert recorder.steps[0]["name"] == "Submit login form"
    assert recorder.steps[0]["status"] == "passed"
    assert recorder.steps[0]["steps"][0]["name"] == "Fill email"
    assert recorder.steps[0]["steps"][0]["status"] == "passed"


def test_step_preserves_the_original_exception():
    recorder = StepRecorder()
    token = install_recorder(recorder)
    error = ValueError("original failure")

    @step("Submit login form")
    def submit():
        raise error

    try:
        with pytest.raises(ValueError) as caught:
            submit()
    finally:
        reset_recorder(token)

    assert caught.value is error
    assert recorder.steps[0]["status"] == "failed"


@pytest.mark.parametrize("parallel", [False, True])
def test_default_reports_share_one_latest_directory(pytester, parallel):
    pytester.makepyfile("""
from pylenium import step

@step("Submit form")
def submit():
    return "done"

def test_one():
    assert submit() == "done"

def test_two():
    assert submit() == "done"
""")
    args = ["-q"] + (["-n", "2"] if parallel else [])
    result = pytester.runpytest_subprocess(*args)
    result.assert_outcomes(passed=2)

    root = pytester.path / "artifacts"
    directories = list((root / "runs").iterdir())
    assert len(directories) == 1
    run = root / "latest"
    assert len(list((run / "steps").glob("*.json"))) == 2
    allure_records = [
        json.loads(path.read_text())
        for path in (run / "allure-results").glob("*-result.json")
    ]
    assert len(allure_records) == 2
    assert all(record["steps"][0]["name"] == "Submit form" for record in allure_records)
    junit = ElementTree.parse(run / "junit.xml")
    assert len(list(junit.iter("testcase"))) == 2
    assert len([node for node in junit.iter("property") if node.get("name") == "pylenium_steps"]) == 2
    records = [json.loads(path.read_text()) for path in (run / "steps").glob("*.json")]
    assert all(record["steps"][0]["name"] == "Submit form" for record in records)


def test_steps_and_junit_work_without_allure(pytester):
    pytester.makepyfile("""
from pylenium import step

@step("Submit form")
def submit():
    return None

def test_example():
    submit()
""")
    pytester.runpytest_subprocess("-q", "-p", "no:allure_pytest").assert_outcomes(passed=1)
    run = pytester.path / "artifacts" / "latest"
    assert (run / "junit.xml").exists()
    assert len(list((run / "steps").glob("*.json"))) == 1
    assert not (run / "allure-results").exists()


def test_next_run_replaces_previous_report(pytester):
    pytester.makepyfile("def test_first(): pass")
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)
    run = pytester.path / "artifacts" / "latest"
    old_file = run / "previous.txt"
    old_file.write_text("old")
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)
    assert not old_file.exists()
    assert (run / "junit.xml").exists()
    assert len(list((pytester.path / "artifacts" / "runs").iterdir())) == 2


def test_concurrent_pytest_invocations_keep_active_evidence(pytester):
    pytester.makepyfile(
        test_slow="""
from pathlib import Path
from time import monotonic, sleep

def test_slow():
    Path("started").touch()
    deadline = monotonic() + 15
    while not Path("release").exists():
        assert monotonic() < deadline, "release signal did not arrive"
        sleep(0.05)
""",
        test_fast="def test_fast(): pass",
    )
    process = pytester.popen((sys.executable, "-mpytest", "-q", "test_slow.py"))
    try:
        deadline = monotonic() + 10
        while not (pytester.path / "started").exists():
            assert process.poll() is None, "first pytest invocation exited early"
            assert monotonic() < deadline, "first pytest invocation did not start"
            sleep(0.05)

        runs = pytester.path / "artifacts" / "runs"
        active = next(runs.iterdir())
        assert (active / "run.json").exists()
        pytester.runpytest_subprocess("-q", "test_fast.py").assert_outcomes(passed=1)
        assert (active / "run.json").exists()
        assert not (active / "junit.xml").exists()
        assert len(list(runs.iterdir())) == 2
    finally:
        (pytester.path / "release").touch()
        try:
            output, errors = process.communicate(timeout=15)
        except TimeoutExpired:
            process.kill()
            output, errors = process.communicate()
            pytest.fail(f"first pytest invocation hung: {output!r} {errors!r}")

    assert process.returncode == 0, f"{output!r} {errors!r}"
    assert (active / "junit.xml").exists()


def test_junit_summary_includes_teardown_step_once(pytester):
    pytester.makeconftest("""
import pytest
from pylenium import step

@pytest.fixture
def resource():
    yield

    @step("Release resource")
    def release():
        pass

    release()
""")
    pytester.makepyfile("def test_cleanup(resource): pass")
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)

    run = pytester.path / "artifacts" / "latest"
    junit = ElementTree.parse(run / "junit.xml")
    summaries = [node.get("value") for node in junit.iter("property")
                 if node.get("name") == "pylenium_steps"]
    assert len(summaries) == 1
    assert "PASSED: Release resource" in summaries[0]
