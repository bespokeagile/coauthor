"""Author attribution engine.

Walks git log, builds author-to-file mapping, clusters files into features
(directory-based clustering), and computes per-author statistics.
"""

import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from . import git_ops


def _file_to_cluster(file_path: str) -> str:
    """Map a file path to a cluster name using first 2 directory levels.

    Examples:
        src/auth/login.py -> src/auth
        tests/unit/test_auth.py -> tests/unit
        README.md -> .
    """
    parts = file_path.split("/")
    if len(parts) >= 3:
        return "/".join(parts[:2])
    elif len(parts) == 2:
        return parts[0]
    else:
        return "."


def _classify_pattern(
    commit_count: int,
    cluster_counts: Dict[str, int],
) -> str:
    """Classify an author's contribution pattern.

    Returns one of: specialist, generalist, hub, peripheral
    """
    if commit_count < 5:
        return "peripheral"

    num_clusters = len(cluster_counts)
    total = sum(cluster_counts.values())

    if total == 0:
        return "peripheral"

    # Find the dominant cluster's share
    max_cluster_commits = max(cluster_counts.values())
    dominant_share = max_cluster_commits / total

    # Hub: high commit count + touches 3+ clusters
    if commit_count >= 20 and num_clusters >= 3:
        return "hub"

    # Specialist: >70% commits in one cluster
    if dominant_share > 0.7:
        return "specialist"

    # Generalist: touches 4+ clusters with no dominant one
    if num_clusters >= 4 and dominant_share <= 0.5:
        return "generalist"

    # Default cases
    if num_clusters >= 4:
        return "generalist"

    return "specialist"


def attribute_authors(
    repo_path: str,
    max_commits: int = 0,
    exclude_bots: bool = True,
) -> Dict:
    """Main attribution function.

    Walks git log, builds author-to-file mapping, clusters files into
    features, and computes per-author statistics.

    Returns a dictionary with 'authors', 'clusters', 'total_commits',
    and 'total_authors' keys.
    """
    commits = git_ops.parse_git_log(
        repo_path,
        max_commits=max_commits,
        exclude_bots=exclude_bots,
    )

    # Per-author tracking
    author_commits = defaultdict(int)  # type: Dict[str, int]
    author_names = {}  # type: Dict[str, str]  # email -> latest name
    author_files = defaultdict(set)  # type: Dict[str, set]
    author_clusters = defaultdict(lambda: defaultdict(int))  # email -> {cluster: count}
    author_first_commit = {}  # type: Dict[str, str]  # email -> date
    author_last_commit = {}  # type: Dict[str, str]  # email -> date

    # Per-cluster tracking
    cluster_files = defaultdict(set)  # type: Dict[str, set]
    cluster_authors = defaultdict(set)  # type: Dict[str, set]
    cluster_commit_counts = defaultdict(lambda: defaultdict(int))  # cluster -> {email: count}

    for commit in commits:
        email = commit["author_email"]
        name = commit["author_name"]
        date = commit["date"]

        author_commits[email] += 1
        author_names[email] = name

        # Track date range
        if email not in author_first_commit:
            author_first_commit[email] = date
            author_last_commit[email] = date
        else:
            # git log is newest-first, so first seen = last commit
            # and last seen = first commit
            author_last_commit[email] = date

        for file_path in commit["files_changed"]:
            cluster = _file_to_cluster(file_path)
            author_files[email].add(file_path)
            author_clusters[email][cluster] += 1
            cluster_files[cluster].add(file_path)
            cluster_authors[cluster].add(email)
            cluster_commit_counts[cluster][email] += 1

    # Build author records
    authors = []
    for email in sorted(author_commits.keys(), key=lambda e: author_commits[e], reverse=True):
        clusters = dict(author_clusters[email])
        primary_cluster = max(clusters, key=clusters.get) if clusters else "."

        pattern = _classify_pattern(author_commits[email], clusters)

        authors.append({
            "email": email,
            "name": author_names[email],
            "commit_count": author_commits[email],
            "first_commit": author_last_commit.get(email, ""),
            "last_commit": author_first_commit.get(email, ""),
            "files_touched": len(author_files[email]),
            "primary_cluster": primary_cluster,
            "clusters": clusters,
            "pattern": pattern,
        })

    # Build cluster records
    clusters_out = {}
    for cluster_name in sorted(cluster_files.keys()):
        author_counts = cluster_commit_counts[cluster_name]
        top_author = ""
        if author_counts:
            top_email = max(author_counts, key=author_counts.get)
            top_author = author_names.get(top_email, top_email)

        clusters_out[cluster_name] = {
            "files": len(cluster_files[cluster_name]),
            "authors": len(cluster_authors[cluster_name]),
            "top_author": top_author,
        }

    return {
        "authors": authors,
        "clusters": clusters_out,
        "total_commits": len(commits),
        "total_authors": len(author_commits),
    }
