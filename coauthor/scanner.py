"""Orchestrator that runs the full analysis pipeline.

Validates the target, runs authorship + impact analysis, and returns
a combined report.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Optional

from . import git_ops
from .authorship import attribute_authors
from .impact import compute_impacts


def run_scan(
    target: str,
    max_commits: int = 0,
    max_files: int = 500,
    exclude_bots: bool = True,
) -> Dict:
    """Run the full analysis pipeline on a git repository.

    Args:
        target: Path to a local git repository.
        max_commits: Maximum number of commits to analyze (0 = all).
        max_files: Maximum number of files to consider.
        exclude_bots: Whether to exclude bot commits.

    Returns:
        Combined report dictionary with authorship, impact, and summary.

    Raises:
        ValueError: If target is not a valid git repository.
    """
    # Validate target
    target = os.path.abspath(target)
    if not os.path.isdir(target):
        raise ValueError("Target path does not exist: %s" % target)

    if not git_ops.is_git_repo(target):
        raise ValueError("Target is not a git repository: %s" % target)

    # Get HEAD SHA
    try:
        commit_sha = git_ops.get_head_sha(target)
    except RuntimeError:
        commit_sha = "unknown"

    # Run authorship analysis
    authorship = attribute_authors(
        target,
        max_commits=max_commits,
        exclude_bots=exclude_bots,
    )

    # Run impact analysis (use max_commits if set, else default 100)
    impact_max = max_commits if max_commits > 0 else 100
    impact = compute_impacts(
        target,
        max_commits=impact_max,
        exclude_bots=exclude_bots,
    )

    # Build summary
    specialists = 0
    generalists = 0
    hubs = 0
    top_contributor = ""
    top_commits = 0

    for author in authorship.get("authors", []):
        pattern = author.get("pattern", "")
        if pattern == "specialist":
            specialists += 1
        elif pattern == "generalist":
            generalists += 1
        elif pattern == "hub":
            hubs += 1

        if author.get("commit_count", 0) > top_commits:
            top_commits = author["commit_count"]
            top_contributor = author.get("name", author.get("email", ""))

    # Find highest impact commit
    highest_impact_commit = ""
    highest_impact = 0.0
    for c in impact.get("commits", []):
        if c.get("structural_impact", 0) > highest_impact:
            highest_impact = c["structural_impact"]
            highest_impact_commit = c.get("hash", "")

    scanned_at = datetime.now(timezone.utc).isoformat()

    return {
        "target": target,
        "commit_sha": commit_sha,
        "scanned_at": scanned_at,
        "authorship": authorship,
        "impact": impact,
        "summary": {
            "total_authors": authorship.get("total_authors", 0),
            "total_commits": authorship.get("total_commits", 0),
            "specialists": specialists,
            "generalists": generalists,
            "hubs": hubs,
            "top_contributor": top_contributor,
            "highest_impact_commit": highest_impact_commit,
        },
    }
