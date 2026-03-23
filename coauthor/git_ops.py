"""Git history extraction. Pure subprocess, no platform dependencies."""

import os
import re
import subprocess
from typing import Dict, List


# Email patterns indicating bot accounts
BOT_PATTERNS = [
    "bot",
    "noreply",
    "dependabot",
    "github-actions",
    "renovate",
]


def _is_bot_email(email: str) -> bool:
    """Check if an email address belongs to a bot account."""
    email_lower = email.lower()
    for pattern in BOT_PATTERNS:
        if pattern in email_lower:
            return True
    return False


def _run_git(args: List[str], cwd: str, timeout: int = 120) -> str:
    """Run a git command and return stdout."""
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "git %s failed: %s" % (args[0], result.stderr.strip())
            )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            "git %s timed out after %d seconds" % (args[0], timeout)
        )
    except FileNotFoundError:
        raise RuntimeError("git is not installed or not on PATH")


def is_git_repo(path: str) -> bool:
    """Check if the given path is inside a git repository."""
    git_dir = os.path.join(path, ".git")
    if os.path.isdir(git_dir):
        return True
    # Also check via git command for worktrees / submodules
    try:
        _run_git(["rev-parse", "--git-dir"], cwd=path, timeout=10)
        return True
    except (RuntimeError, OSError):
        return False


def get_head_sha(path: str) -> str:
    """Return the HEAD commit SHA for the repository at path."""
    output = _run_git(["rev-parse", "HEAD"], cwd=path, timeout=10)
    return output.strip()


def parse_git_log(
    repo_path: str,
    max_commits: int = 0,
    exclude_bots: bool = True,
) -> List[Dict]:
    """Parse git log and return structured commit data.

    Each entry contains:
        hash, author_name, author_email, date, message, files_changed
    """
    # Use a delimiter unlikely to appear in commit messages
    sep = "---COAUTHOR_SEP---"
    fmt = sep.join(["%H", "%an", "%ae", "%aI", "%s"])

    args = [
        "log",
        "--format=%s" % fmt,
        "--name-only",
    ]
    if max_commits > 0:
        args.append("-n")
        args.append(str(max_commits))

    output = _run_git(args, cwd=repo_path)
    if not output.strip():
        return []

    commits = []
    current_commit = None

    for line in output.split("\n"):
        line = line.rstrip()

        if sep in line:
            # Save previous commit
            if current_commit is not None:
                commits.append(current_commit)

            parts = line.split(sep)
            if len(parts) < 5:
                continue

            email = parts[2]
            if exclude_bots and _is_bot_email(email):
                current_commit = None
                continue

            current_commit = {
                "hash": parts[0],
                "author_name": parts[1],
                "author_email": email,
                "date": parts[3],
                "message": parts[4],
                "files_changed": [],
            }
        elif line and current_commit is not None:
            current_commit["files_changed"].append(line)

    # Don't forget the last commit
    if current_commit is not None:
        commits.append(current_commit)

    return commits


def get_file_blame_summary(repo_path: str, file_path: str) -> Dict[str, int]:
    """Run git blame on a file and return {email: line_count} mapping."""
    try:
        output = _run_git(
            ["blame", "--line-porcelain", file_path],
            cwd=repo_path,
        )
    except RuntimeError:
        return {}

    email_counts = {}  # type: Dict[str, int]
    email_pattern = re.compile(r"^author-mail <(.+)>$")

    for line in output.split("\n"):
        match = email_pattern.match(line)
        if match:
            email = match.group(1)
            email_counts[email] = email_counts.get(email, 0) + 1

    return email_counts
