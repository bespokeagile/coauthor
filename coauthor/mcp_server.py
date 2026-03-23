"""Coauthor MCP server -- code authorship analysis via Model Context Protocol."""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Optional

log = logging.getLogger(__name__)


def _build_instructions() -> str:
    """Build context-aware instructions based on user's scan history."""
    scan_count = 0
    last_repo = ""
    try:
        from coauthor.store import list_scans
        scans = list_scans(limit=5)
        scan_count = len(scans)
        if scans:
            last_repo = scans[0].get("repo_path", "")
    except Exception:
        pass  # DB not initialized yet, treat as new user

    base = (
        "Coauthor is an open-source code authorship analysis tool. It scans "
        "git repositories to map who wrote what, identify contribution "
        "patterns (specialists, generalists, hubs), compute structural "
        "impact of commits, and surface bus-factor risks.\n\n"
    )

    if scan_count == 0:
        base += (
            "## Welcome -- First Time\n\n"
            "This user has never run a scan. Get them to a meaningful "
            "result fast.\n\n"
            "### Flow\n\n"
            "1. **One question**: \"Which repository do you want to "
            "analyze?\" If the user is in a project directory, offer to "
            "scan it directly.\n\n"
            "2. **Run the scan immediately** with coauthor_scan. Don't "
            "explain what a scan is. Just do it.\n\n"
            "3. **Present results -- lead with what's interesting**. Say: "
            "\"This repo has N authors. The top contributor is X with Y "
            "commits. There are Z specialists and W generalists.\" Then "
            "highlight any bus-factor risks: \"The auth/ cluster has only "
            "one contributor -- that's a single point of failure.\"\n\n"
            "4. **One concrete next action**. Suggest coauthor_who_owns "
            "for a specific file or directory they care about, or "
            "coauthor_risk_map for the full bus-factor picture.\n\n"
            "### Tone rules\n\n"
            "- Lead with insights, not raw data.\n"
            "- Frame bus-factor as opportunity (\"this area would benefit "
            "from a second contributor\"), not blame.\n"
            "- Use author names, not email addresses, in conversation.\n"
            "- This is about understanding the team, not auditing it.\n\n"
        )
    else:
        base += (
            "## Returning User\n\n"
            "This user has %d previous scan(s). " % scan_count
        )
        if last_repo:
            base += "Most recent: `%s`. " % last_repo
        base += (
            "Skip introductions. Offer to:\n"
            "- Re-scan to see changes (coauthor_scan)\n"
            "- Compare scans to see team evolution (coauthor_diff)\n"
            "- Check ownership of specific files (coauthor_who_owns)\n"
            "- Review bus-factor risks (coauthor_risk_map)\n\n"
            "When showing results, compare to previous scans: "
            "\"2 new authors since last scan. The auth/ cluster now has "
            "a second contributor -- bus factor improved.\"\n\n"
        )

    base += (
        "## Recommended tool chains\n\n"
        "- **Quick check**: coauthor_scan -> coauthor_summary\n"
        "- **Ownership query**: coauthor_who_owns (no scan needed for files)\n"
        "- **Risk assessment**: coauthor_scan -> coauthor_risk_map\n"
        "- **Team evolution**: coauthor_scan -> coauthor_diff (compare with "
        "previous)\n"
        "- **Deep dive**: coauthor_scan -> coauthor_authors -> "
        "coauthor_signatures -> coauthor_risk_map\n"
        "- **Full report**: coauthor_scan -> coauthor_report (json or "
        "markdown)\n"
    )
    return base


def _json(obj: object) -> str:
    """Serialize to compact JSON, handling non-serializable types."""
    def _default(o):
        if hasattr(o, "isoformat"):
            return o.isoformat()
        if isinstance(o, set):
            return list(o)
        if hasattr(o, "__dict__"):
            return o.__dict__
        return str(o)
    return json.dumps(obj, default=_default, indent=2)


def _err(e: Exception) -> str:
    return _json({"error": str(e), "type": type(e).__name__})


def _resolve_scan(scan_id: str = "") -> Optional[dict]:
    """Load a scan by ID, or the latest scan if no ID given."""
    from coauthor.store import get_scan, list_scans
    if scan_id:
        return get_scan(scan_id)
    scans = list_scans(limit=1)
    if not scans:
        return None
    return get_scan(scans[0]["id"])


# ---------------------------------------------------------------------------
# MCP app factory
# ---------------------------------------------------------------------------

def create_mcp_app():
    """Create the FastMCP instance and register all tools."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "Coauthor",
        instructions=_build_instructions(),
    )

    # -------------------------------------------------------------------
    # Tool 1: Scan a repository
    # -------------------------------------------------------------------

    @mcp.tool()
    def coauthor_scan(
        target: str,
        max_commits: int = 0,
        max_files: int = 500,
    ) -> str:
        """Run a full authorship and impact scan on a git repository.

        Analyzes git history to map authors to code clusters, classify
        contribution patterns, and compute structural impact of commits.

        Args:
            target: Path to a local git repository.
            max_commits: Maximum commits to analyze (0 = all).
            max_files: Maximum files to consider.

        Returns:
            JSON report with authorship, impact, summary, and scan ID.
        """
        try:
            from coauthor.scanner import run_scan
            from coauthor.store import save_scan

            report = run_scan(
                target=target,
                max_commits=max_commits,
                max_files=max_files,
            )

            scan_id = uuid.uuid4().hex[:12]
            try:
                save_scan(
                    scan_id=scan_id,
                    repo_path=report.get("target", target),
                    commit_sha=report.get("commit_sha", ""),
                    report=report,
                )
            except Exception as e:
                log.warning("Could not save scan: %s", e)

            result = {
                "scan_id": scan_id,
                "target": report.get("target", target),
                "commit_sha": report.get("commit_sha", ""),
                "scanned_at": report.get("scanned_at", ""),
                "summary": report.get("summary", {}),
            }
            return _json(result)
        except Exception as e:
            return _err(e)

    # -------------------------------------------------------------------
    # Tool 2: Get authors
    # -------------------------------------------------------------------

    @mcp.tool()
    def coauthor_authors(scan_id: str = "") -> str:
        """Get the author table from the latest or a specific scan.

        Shows each author's name, email, commit count, contribution
        pattern (specialist/generalist/hub/peripheral), and primary
        code cluster.

        Args:
            scan_id: Scan ID to retrieve (default: latest scan).
        """
        try:
            report = _resolve_scan(scan_id)
            if report is None:
                return _json({"error": "No scan found. Run coauthor_scan first."})

            authorship = report.get("authorship", {})
            authors = authorship.get("authors", [])
            return _json({
                "total_authors": authorship.get("total_authors", 0),
                "total_commits": authorship.get("total_commits", 0),
                "authors": authors,
            })
        except Exception as e:
            return _err(e)

    # -------------------------------------------------------------------
    # Tool 3: Get impact commits
    # -------------------------------------------------------------------

    @mcp.tool()
    def coauthor_impacts(scan_id: str = "", limit: int = 10) -> str:
        """Get the top structural-impact commits from a scan.

        Structural impact measures how broadly a commit affects the
        codebase across clusters. High-impact commits touch many files
        across many areas.

        Args:
            scan_id: Scan ID to retrieve (default: latest scan).
            limit: Maximum number of commits to return (default: 10).
        """
        try:
            report = _resolve_scan(scan_id)
            if report is None:
                return _json({"error": "No scan found. Run coauthor_scan first."})

            impact = report.get("impact", {})
            commits = impact.get("commits", [])
            sorted_commits = sorted(
                commits,
                key=lambda c: c.get("structural_impact", 0),
                reverse=True,
            )[:limit]

            return _json({
                "total_commits": impact.get("total_commits", 0),
                "top_commits": sorted_commits,
                "author_impact": impact.get("author_impact", {}),
            })
        except Exception as e:
            return _err(e)

    # -------------------------------------------------------------------
    # Tool 4: Who owns this file/directory?
    # -------------------------------------------------------------------

    @mcp.tool()
    def coauthor_who_owns(target: str, path: str) -> str:
        """Find who owns a specific file or directory in a repository.

        For files: uses git blame to show line-by-line ownership.
        For directories: aggregates authorship across all files in
        that directory tree.

        This is the most useful tool for quick ownership questions
        like "who should I ask about the auth module?"

        Args:
            target: Path to the git repository.
            path: Relative path within the repo (file or directory).
        """
        try:
            target = os.path.abspath(target)
            full_path = os.path.join(target, path)

            if os.path.isfile(full_path):
                # File: use git blame summary
                from coauthor.git_ops import get_file_blame_summary
                blame = get_file_blame_summary(target, path)
                if not blame:
                    return _json({
                        "path": path,
                        "type": "file",
                        "error": "Could not get blame data. File may be untracked or binary.",
                    })

                total_lines = sum(blame.values())
                owners = []
                for email, lines in sorted(blame.items(), key=lambda x: x[1], reverse=True):
                    pct = round(100.0 * lines / total_lines, 1) if total_lines > 0 else 0
                    owners.append({
                        "email": email,
                        "lines": lines,
                        "percentage": pct,
                    })

                return _json({
                    "path": path,
                    "type": "file",
                    "total_lines": total_lines,
                    "owners": owners,
                    "primary_owner": owners[0]["email"] if owners else "unknown",
                })

            elif os.path.isdir(full_path):
                # Directory: walk authorship data from latest scan
                # or run a lightweight attribution
                from coauthor.authorship import attribute_authors

                authorship = attribute_authors(target, max_commits=0)
                clusters = authorship.get("clusters", {})
                authors = authorship.get("authors", [])

                # Find clusters that match the given path prefix
                path_normalized = path.rstrip("/")
                matching_clusters = {}
                for cluster_name, cluster_data in clusters.items():
                    if cluster_name == path_normalized or cluster_name.startswith(path_normalized + "/"):
                        matching_clusters[cluster_name] = cluster_data

                if not matching_clusters:
                    # Try matching as a top-level prefix
                    for cluster_name, cluster_data in clusters.items():
                        if path_normalized in cluster_name:
                            matching_clusters[cluster_name] = cluster_data

                if not matching_clusters:
                    return _json({
                        "path": path,
                        "type": "directory",
                        "error": "No authorship data found for this directory.",
                    })

                # Aggregate authors across matching clusters
                author_commits = {}  # type: dict
                for author in authors:
                    author_cluster_data = author.get("clusters", {})
                    total_in_path = 0
                    for cluster_name in matching_clusters:
                        total_in_path += author_cluster_data.get(cluster_name, 0)
                    if total_in_path > 0:
                        author_commits[author.get("email", "")] = {
                            "name": author.get("name", ""),
                            "email": author.get("email", ""),
                            "commits_in_path": total_in_path,
                            "pattern": author.get("pattern", ""),
                        }

                sorted_authors = sorted(
                    author_commits.values(),
                    key=lambda a: a["commits_in_path"],
                    reverse=True,
                )

                total_commits_in_path = sum(a["commits_in_path"] for a in sorted_authors)
                for a in sorted_authors:
                    a["percentage"] = round(
                        100.0 * a["commits_in_path"] / total_commits_in_path, 1
                    ) if total_commits_in_path > 0 else 0

                return _json({
                    "path": path,
                    "type": "directory",
                    "clusters": list(matching_clusters.keys()),
                    "total_commits": total_commits_in_path,
                    "owners": sorted_authors,
                    "primary_owner": sorted_authors[0]["email"] if sorted_authors else "unknown",
                })

            else:
                return _json({
                    "path": path,
                    "error": "Path not found: %s" % full_path,
                })
        except Exception as e:
            return _err(e)

    # -------------------------------------------------------------------
    # Tool 5: Risk map (bus factor)
    # -------------------------------------------------------------------

    @mcp.tool()
    def coauthor_risk_map(scan_id: str = "") -> str:
        """Bus factor analysis across all code clusters.

        For each cluster (directory grouping), counts unique authors.
        Clusters with only 1 author are critical risk -- if that person
        leaves, no one else knows the code.

        Args:
            scan_id: Scan ID to analyze (default: latest scan).
        """
        try:
            report = _resolve_scan(scan_id)
            if report is None:
                return _json({"error": "No scan found. Run coauthor_scan first."})

            authorship = report.get("authorship", {})
            clusters = authorship.get("clusters", {})

            risk_entries = []
            critical_count = 0
            moderate_count = 0
            healthy_count = 0

            for cluster_name, cluster_data in sorted(clusters.items()):
                author_count = cluster_data.get("authors", 0)
                file_count = cluster_data.get("files", 0)
                top_author = cluster_data.get("top_author", "")

                if author_count <= 1:
                    risk_level = "critical"
                    critical_count += 1
                elif author_count == 2:
                    risk_level = "moderate"
                    moderate_count += 1
                else:
                    risk_level = "healthy"
                    healthy_count += 1

                risk_entries.append({
                    "cluster": cluster_name,
                    "authors": author_count,
                    "files": file_count,
                    "top_author": top_author,
                    "risk_level": risk_level,
                })

            return _json({
                "total_clusters": len(clusters),
                "critical": critical_count,
                "moderate": moderate_count,
                "healthy": healthy_count,
                "clusters": risk_entries,
            })
        except Exception as e:
            return _err(e)

    # -------------------------------------------------------------------
    # Tool 6: Author signatures
    # -------------------------------------------------------------------

    @mcp.tool()
    def coauthor_signatures(scan_id: str = "") -> str:
        """Author contribution pattern summary.

        Classifies each author as a specialist (deep in one area),
        generalist (broad across many areas), hub (high volume, many
        areas), or peripheral (few commits).

        Args:
            scan_id: Scan ID to analyze (default: latest scan).
        """
        try:
            report = _resolve_scan(scan_id)
            if report is None:
                return _json({"error": "No scan found. Run coauthor_scan first."})

            authorship = report.get("authorship", {})
            authors = authorship.get("authors", [])

            patterns = {
                "specialist": [],
                "generalist": [],
                "hub": [],
                "peripheral": [],
            }

            for author in authors:
                pattern = author.get("pattern", "peripheral")
                entry = {
                    "name": author.get("name", ""),
                    "email": author.get("email", ""),
                    "commit_count": author.get("commit_count", 0),
                    "primary_cluster": author.get("primary_cluster", ""),
                    "cluster_count": len(author.get("clusters", {})),
                }
                if pattern in patterns:
                    patterns[pattern].append(entry)
                else:
                    patterns["peripheral"].append(entry)

            return _json({
                "specialist_count": len(patterns["specialist"]),
                "generalist_count": len(patterns["generalist"]),
                "hub_count": len(patterns["hub"]),
                "peripheral_count": len(patterns["peripheral"]),
                "specialists": patterns["specialist"],
                "generalists": patterns["generalist"],
                "hubs": patterns["hub"],
                "peripheral": patterns["peripheral"],
            })
        except Exception as e:
            return _err(e)

    # -------------------------------------------------------------------
    # Tool 7: Scan history
    # -------------------------------------------------------------------

    @mcp.tool()
    def coauthor_history(limit: int = 10) -> str:
        """List past scans with their IDs, repos, and dates.

        Args:
            limit: Maximum number of scans to return (default: 10).
        """
        try:
            from coauthor.store import list_scans
            scans = list_scans(limit=limit)
            return _json({
                "count": len(scans),
                "scans": scans,
            })
        except Exception as e:
            return _err(e)

    # -------------------------------------------------------------------
    # Tool 8: Diff two scans
    # -------------------------------------------------------------------

    @mcp.tool()
    def coauthor_diff(scan_id_1: str, scan_id_2: str) -> str:
        """Compare two scans to see team evolution.

        Shows new authors, departed authors, pattern changes
        (e.g. specialist -> hub), and cluster ownership shifts.

        Args:
            scan_id_1: The earlier scan ID.
            scan_id_2: The later scan ID.
        """
        try:
            from coauthor.store import get_scan

            s1 = get_scan(scan_id_1)
            s2 = get_scan(scan_id_2)
            if not s1:
                return _json({"error": "Scan %s not found" % scan_id_1})
            if not s2:
                return _json({"error": "Scan %s not found" % scan_id_2})

            # Extract author sets
            a1 = s1.get("authorship", {})
            a2 = s2.get("authorship", {})
            authors1 = {a["email"]: a for a in a1.get("authors", [])}
            authors2 = {a["email"]: a for a in a2.get("authors", [])}

            emails1 = set(authors1.keys())
            emails2 = set(authors2.keys())

            new_authors = []
            for email in sorted(emails2 - emails1):
                a = authors2[email]
                new_authors.append({
                    "email": email,
                    "name": a.get("name", ""),
                    "commit_count": a.get("commit_count", 0),
                    "pattern": a.get("pattern", ""),
                })

            departed_authors = []
            for email in sorted(emails1 - emails2):
                a = authors1[email]
                departed_authors.append({
                    "email": email,
                    "name": a.get("name", ""),
                    "commit_count": a.get("commit_count", 0),
                    "pattern": a.get("pattern", ""),
                })

            pattern_changes = []
            for email in sorted(emails1 & emails2):
                p1 = authors1[email].get("pattern", "")
                p2 = authors2[email].get("pattern", "")
                if p1 != p2:
                    pattern_changes.append({
                        "email": email,
                        "name": authors2[email].get("name", ""),
                        "old_pattern": p1,
                        "new_pattern": p2,
                    })

            # Cluster changes
            clusters1 = set(a1.get("clusters", {}).keys())
            clusters2 = set(a2.get("clusters", {}).keys())
            new_clusters = sorted(clusters2 - clusters1)
            removed_clusters = sorted(clusters1 - clusters2)

            summary1 = s1.get("summary", {})
            summary2 = s2.get("summary", {})

            return _json({
                "scan_1": {
                    "id": scan_id_1,
                    "scanned_at": s1.get("scanned_at", ""),
                    "total_authors": summary1.get("total_authors", a1.get("total_authors", 0)),
                    "total_commits": summary1.get("total_commits", a1.get("total_commits", 0)),
                },
                "scan_2": {
                    "id": scan_id_2,
                    "scanned_at": s2.get("scanned_at", ""),
                    "total_authors": summary2.get("total_authors", a2.get("total_authors", 0)),
                    "total_commits": summary2.get("total_commits", a2.get("total_commits", 0)),
                },
                "new_authors": new_authors,
                "departed_authors": departed_authors,
                "pattern_changes": pattern_changes,
                "new_clusters": new_clusters,
                "removed_clusters": removed_clusters,
            })
        except Exception as e:
            return _err(e)

    # -------------------------------------------------------------------
    # Tool 9: Full report
    # -------------------------------------------------------------------

    @mcp.tool()
    def coauthor_report(scan_id: str = "", format: str = "json") -> str:
        """Get the full scan report in a specified format.

        Args:
            scan_id: Scan ID to retrieve (default: latest scan).
            format: Output format -- "json" or "markdown".
        """
        try:
            report = _resolve_scan(scan_id)
            if report is None:
                return _json({"error": "No scan found. Run coauthor_scan first."})

            if format == "markdown":
                from coauthor.formats import export_markdown
                return export_markdown(report)
            elif format == "json":
                from coauthor.formats import export_json
                return export_json(report)
            else:
                return _json({"error": "Unknown format: %s. Use json or markdown." % format})
        except Exception as e:
            return _err(e)

    # -------------------------------------------------------------------
    # Tool 10: Natural language summary
    # -------------------------------------------------------------------

    @mcp.tool()
    def coauthor_summary(scan_id: str = "") -> str:
        """One-paragraph natural language summary of a scan.

        Provides a concise, human-readable overview of who works on
        this codebase, contribution patterns, and any notable risks.

        Args:
            scan_id: Scan ID to summarize (default: latest scan).
        """
        try:
            report = _resolve_scan(scan_id)
            if report is None:
                return _json({"error": "No scan found. Run coauthor_scan first."})

            summary = report.get("summary", {})
            authorship = report.get("authorship", {})
            target = report.get("target", "unknown")
            repo_name = os.path.basename(target) if target else "unknown"

            total_authors = summary.get("total_authors", 0)
            total_commits = summary.get("total_commits", 0)
            specialists = summary.get("specialists", 0)
            generalists = summary.get("generalists", 0)
            hubs = summary.get("hubs", 0)
            top_contributor = summary.get("top_contributor", "unknown")

            # Count bus-factor risks
            clusters = authorship.get("clusters", {})
            critical_clusters = []
            for cluster_name, cluster_data in clusters.items():
                if cluster_data.get("authors", 0) <= 1:
                    critical_clusters.append(cluster_name)

            # Build natural language summary
            parts = []
            parts.append(
                "The %s repository has %d author(s) across %d commit(s)."
                % (repo_name, total_authors, total_commits)
            )

            if top_contributor:
                parts.append(
                    "The top contributor is %s." % top_contributor
                )

            pattern_parts = []
            if hubs:
                pattern_parts.append("%d hub(s)" % hubs)
            if generalists:
                pattern_parts.append("%d generalist(s)" % generalists)
            if specialists:
                pattern_parts.append("%d specialist(s)" % specialists)
            if pattern_parts:
                parts.append(
                    "The team includes %s." % ", ".join(pattern_parts)
                )

            if critical_clusters:
                if len(critical_clusters) <= 3:
                    cluster_list = ", ".join(critical_clusters)
                else:
                    cluster_list = (
                        ", ".join(critical_clusters[:3])
                        + " and %d more" % (len(critical_clusters) - 3)
                    )
                parts.append(
                    "Bus-factor risk: %d cluster(s) have only one author (%s)."
                    % (len(critical_clusters), cluster_list)
                )
            else:
                parts.append(
                    "No critical bus-factor risks detected -- all clusters "
                    "have multiple contributors."
                )

            text = " ".join(parts)
            return _json({"summary": text})
        except Exception as e:
            return _err(e)

    return mcp


# ---------------------------------------------------------------------------
# Server entry points
# ---------------------------------------------------------------------------

def run_mcp_server():
    """Start the Coauthor MCP server via stdio transport."""
    app = create_mcp_app()
    app.run()


if __name__ == "__main__":
    run_mcp_server()
