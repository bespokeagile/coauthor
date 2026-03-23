"""Commit impact analysis.

Computes structural impact for each commit based on files changed
and their cluster spread.
"""

from collections import defaultdict
from typing import Dict, List, Optional

from . import git_ops


def _file_to_cluster(file_path: str) -> str:
    """Map a file path to a cluster name using first 2 directory levels."""
    parts = file_path.split("/")
    if len(parts) >= 3:
        return "/".join(parts[:2])
    elif len(parts) == 2:
        return parts[0]
    else:
        return "."


def _truncate_message(message: str, max_len: int = 80) -> str:
    """Truncate a commit message to max_len characters."""
    if len(message) <= max_len:
        return message
    return message[:max_len - 3] + "..."


def _compute_structural_impact(files_changed: int, clusters_touched: int) -> float:
    """Compute structural impact score.

    Formula: impact = files_changed * (1 + clusters_touched * 0.5)
    """
    return files_changed * (1.0 + clusters_touched * 0.5)


def compute_impacts(
    repo_path: str,
    max_commits: int = 100,
    exclude_bots: bool = True,
) -> Dict:
    """Compute structural impact for each commit.

    For each commit, structural impact is based on files changed and
    their cluster spread.

    Returns a dictionary with 'commits', 'author_impact', and
    'total_commits' keys.
    """
    commits = git_ops.parse_git_log(
        repo_path,
        max_commits=max_commits,
        exclude_bots=exclude_bots,
    )

    commit_records = []
    # email -> tracking dict
    author_impact = defaultdict(lambda: {
        "total_impact": 0.0,
        "avg_impact": 0.0,
        "commits": 0,
        "max_impact": 0.0,
        "max_impact_commit": "",
    })

    for commit in commits:
        files = commit["files_changed"]
        files_changed = len(files)

        # Determine clusters touched
        clusters = set()
        for f in files:
            clusters.add(_file_to_cluster(f))
        clusters_touched = len(clusters)

        impact = _compute_structural_impact(files_changed, clusters_touched)

        record = {
            "hash": commit["hash"],
            "author_name": commit["author_name"],
            "author_email": commit["author_email"],
            "date": commit["date"],
            "message": _truncate_message(commit["message"]),
            "files_changed": files_changed,
            "clusters_touched": clusters_touched,
            "structural_impact": round(impact, 2),
        }
        commit_records.append(record)

        # Update author impact
        email = commit["author_email"]
        ai = author_impact[email]
        ai["total_impact"] += impact
        ai["commits"] += 1
        if impact > ai["max_impact"]:
            ai["max_impact"] = impact
            ai["max_impact_commit"] = commit["hash"]

    # Finalize author impact averages and round
    author_impact_out = {}
    for email, ai in author_impact.items():
        if ai["commits"] > 0:
            ai["avg_impact"] = round(ai["total_impact"] / ai["commits"], 2)
        ai["total_impact"] = round(ai["total_impact"], 2)
        # Remove internal tracking field
        final = {
            "total_impact": ai["total_impact"],
            "avg_impact": ai["avg_impact"],
            "commits": ai["commits"],
            "max_impact_commit": ai["max_impact_commit"],
        }
        author_impact_out[email] = final

    return {
        "commits": commit_records,
        "author_impact": author_impact_out,
        "total_commits": len(commit_records),
    }
