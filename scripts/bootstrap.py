#!/usr/bin/env python3
"""Create the workspace and optionally install the two upstream Agent Skills."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from check_environment import inspect_environment
from common import SKILL_ROOT, load_config, sha256_file, workspace_layout


DEPENDENCIES = (
    ("promo-video-maker", "https://github.com/liyupi/ai-promo-video-maker.git", "PROMO_VIDEO_SKILL_ROOT"),
    ("jianying-editor-skill", "https://github.com/luoluoluo22/jianying-editor-skill.git", "JY_SKILL_ROOT"),
)


def select_runtime_python(workspace: Path) -> str | None:
    """Find a Python 3.10+ interpreter for the isolated automation runtime."""
    executable_name = "python.exe" if os.name == "nt" else "python"
    bin_name = "Scripts" if os.name == "nt" else "bin"
    candidates = [
        os.environ.get("QUICKMARKER_PYTHON"),
        str(workspace.resolve() / ".venv-jianying" / bin_name / executable_name),
        str(workspace.resolve() / ".venv" / bin_name / executable_name),
        shutil.which("python3.12"),
        shutil.which("python3.11"),
        shutil.which("python3.10"),
        sys.executable,
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).exists():
            continue
        proc = subprocess.run(
            [candidate, "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"],
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            return candidate
    return None


def dependency_candidates(name: str, env_name: str) -> list[Path]:
    """Return override and common native/universal installation locations."""
    override = os.environ.get(env_name)
    aliases = [name]
    if name == "promo-video-maker":
        aliases.append("ai-promo-video-maker")
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser().resolve())
    for base in (Path.home() / ".agents" / "skills", Path.home() / ".codex" / "skills", Path.home() / ".claude" / "skills"):
        candidates.extend(base / alias for alias in aliases)
    return list(dict.fromkeys(candidates))


def ensure_dependency(name: str, url: str, env_name: str, install: bool) -> dict[str, Any]:
    """Validate, or clone when authorized by --install, one upstream skill."""
    candidates = dependency_candidates(name, env_name)
    existing = next((path for path in candidates if (path / "SKILL.md").is_file()), None)
    destination = existing or candidates[0]
    skill_file = destination / "SKILL.md"
    if existing:
        commit = None
        if (destination / ".git").exists() and shutil.which("git"):
            proc = subprocess.run(
                ["git", "-C", str(destination), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            commit = proc.stdout.strip() or None
        return {"name": name, "status": "ready", "path": str(destination), "commit": commit}
    if destination.exists():
        return {
            "name": name,
            "status": "broken",
            "path": str(destination),
            "error": "目录存在但缺少 SKILL.md；请移走该目录后重试。",
        }
    if not install:
        return {"name": name, "status": "missing", "path": str(destination), "install_command": f"git clone {url} {destination}"}
    if not shutil.which("git"):
        return {"name": name, "status": "failed", "path": str(destination), "error": "未找到 git。"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "clone", "--depth", "1", url, str(destination)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not skill_file.is_file():
        return {
            "name": name,
            "status": "failed",
            "path": str(destination),
            "error": (proc.stderr or proc.stdout).strip()[-1200:],
        }
    return {"name": name, "status": "installed", "path": str(destination)}


def run_install(command: list[str], cwd: Path | None = None) -> dict[str, Any]:
    """Run an explicitly requested dependency installation with compact diagnostics."""
    try:
        proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    except OSError as exc:
        return {"status": "failed", "command": command, "error": str(exc)}
    if proc.returncode:
        output = (proc.stderr or proc.stdout).strip()
        return {"status": "failed", "command": command, "error": output[-1600:]}
    return {"status": "installed", "command": command}


def ensure_runtime(workspace: Path, dependencies: list[dict[str, Any]], install: bool) -> dict[str, Any]:
    """Create a workspace-local Python runtime and install declared free dependencies."""
    runtime_root = workspace.resolve() / ".quickmarker-runtime"
    venv = runtime_root / "venv"
    python_path = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    report: dict[str, Any] = {"path": str(runtime_root), "python": str(python_path), "steps": []}
    runtime_python = select_runtime_python(workspace)
    report["bootstrap_python"] = runtime_python
    if not runtime_python:
        report.update(status="failed", error="Python 3.10 or newer is required. Install it, or set QUICKMARKER_PYTHON.")
        return report
    if not install:
        report["status"] = "ready" if python_path.exists() else "not_installed"
        return report
    runtime_root.mkdir(parents=True, exist_ok=True)
    if not python_path.exists():
        step = run_install([runtime_python, "-m", "venv", str(venv)])
        report["steps"].append(step)
        if step["status"] == "failed":
            report["status"] = "failed"
            return report
    for dependency in dependencies:
        if dependency.get("status") not in {"ready", "installed"}:
            continue
        root = Path(dependency["path"])
        requirements = root / "requirements.txt"
        if requirements.is_file() and requirements.stat().st_size:
            stamp = runtime_root / "stamps" / f"{dependency['name']}-{sha256_file(requirements)[:16]}.done"
            if stamp.exists():
                report["steps"].append({"status": "ready", "detail": f"requirements unchanged: {dependency['name']}"})
            else:
                step = run_install([str(python_path), "-m", "pip", "install", "-r", str(requirements)])
                report["steps"].append(step)
                if step["status"] == "installed":
                    stamp.parent.mkdir(parents=True, exist_ok=True)
                    stamp.write_text("installed\n", encoding="utf-8")
        if dependency["name"] == "promo-video-maker" and (root / "package.json").is_file() and not (root / "node_modules").exists():
            npm = shutil.which("npm")
            if npm:
                report["steps"].append(run_install([npm, "install"], cwd=root))
            else:
                report["steps"].append({"status": "failed", "error": "npm not found"})
    report["status"] = "failed" if any(step["status"] == "failed" for step in report["steps"]) else "ready"
    return report


def bootstrap(workspace: Path, install: bool = False) -> dict[str, Any]:
    """Initialize state and inspect/install dependencies without paid services."""
    paths = workspace_layout(workspace)
    dependencies = [ensure_dependency(*spec, install=install) for spec in DEPENDENCIES]
    runtime = ensure_runtime(workspace, dependencies, install=install)
    return {
        "workspace": str(workspace.resolve()),
        "layout": {key: str(value) for key, value in paths.items()},
        "environment": inspect_environment(),
        "dependencies": dependencies,
        "runtime": runtime,
        "config": load_config(),
        "skill_root": str(SKILL_ROOT),
        "ready": all(item["status"] in {"ready", "installed"} for item in dependencies)
        and runtime["status"] in {"ready", "not_installed"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="User project workspace.")
    parser.add_argument("--install", action="store_true", help="Clone missing free/open-source dependencies.")
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()
    report = bootstrap(Path(args.workspace), install=args.install)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

