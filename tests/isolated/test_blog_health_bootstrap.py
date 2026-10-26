"""Run the workflow bootstrap and import actual config without live credentials."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]


def isolated_env(tmp_path):
    env = {
        key: os.environ[key]
        for key in (
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "HOME",
            "APPDATA",
            "USERPROFILE",
        )
        if key in os.environ
    }
    env.update(
        FLASK_ENV="development",
        DATABASE_URL="sqlite:///bootstrap_test.db",
        GITHUB_ENV=str(tmp_path / "github_env"),
    )
    return env


def import_config(env):
    return subprocess.run(
        [sys.executable, "-c", "import runpy; runpy.run_path('config.py')"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_config_import_without_bootstrap_requires_secret(tmp_path):
    result = import_config(isolated_env(tmp_path))
    assert result.returncode != 0
    assert "SECRET_KEY must be set in production" in result.stderr


def test_workflow_bootstrap_allows_config_import_without_logging_secret(tmp_path):
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/blog-health.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["blog-health"]["steps"]
    smoke = next(step for step in steps if step["name"] == "Run blog smoke check")
    prefix = next(
        line.strip().removesuffix("\\").strip()
        for line in smoke["run"].splitlines()
        if line.strip().startswith("SECRET_KEY=")
    )
    assert "SECRET_KEY" not in workflow.get("env", {})
    env = isolated_env(tmp_path)
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    bash = (
        str(git_bash) if os.name == "nt" and git_bash.exists() else shutil.which("bash")
    )
    assert bash, "bash is required to exercise the actual workflow shell"
    probe = (
        "import os,runpy; runpy.run_path('config.py'); "
        "assert len(os.environ['SECRET_KEY']) >= 32; print('CONFIG_IMPORT=PASS')"
    )
    command = (
        prefix
        + " "
        + shlex.quote(sys.executable.replace("\\", "/"))
        + " -c "
        + shlex.quote(probe)
    )
    result = subprocess.run(
        [bash, "--noprofile", "--norc", "-eo", "pipefail", "-c", command],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "CONFIG_IMPORT=PASS"
    assert result.stderr == ""
    assert "SECRET_KEY" not in env
    assert not Path(env["GITHUB_ENV"]).exists()
