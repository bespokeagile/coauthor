"""Export formats for scan reports.

Provides JSON and Markdown export. No external dependencies.
"""

import json
from typing import Dict


def export_json(report: Dict) -> str:
    """Export report as formatted JSON."""
    return json.dumps(report, indent=2, default=str)


def export_markdown(report: Dict) -> str:
    """Export report as a Markdown document with tables."""
    lines = []
    summary = report.get("summary", {})
    target = report.get("target", "unknown")

    lines.append("# Coauthor Report")
    lines.append("")
    lines.append("**Repository**: %s" % target)
    lines.append("**Scanned at**: %s" % report.get("scanned_at", ""))
    lines.append("**Commit**: %s" % report.get("commit_sha", "")[:8])
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append("| Total authors | %d |" % summary.get("total_authors", 0))
    lines.append("| Total commits | %d |" % summary.get("total_commits", 0))
    lines.append("| Specialists | %d |" % summary.get("specialists", 0))
    lines.append("| Generalists | %d |" % summary.get("generalists", 0))
    lines.append("| Hubs | %d |" % summary.get("hubs", 0))
    lines.append("| Top contributor | %s |" % summary.get("top_contributor", ""))
    lines.append("")

    # Authors table
    authorship = report.get("authorship", {})
    authors = authorship.get("authors", [])
    if authors:
        lines.append("## Authors")
        lines.append("")
        lines.append("| Name | Email | Pattern | Commits | Files | Primary Cluster |")
        lines.append("|------|-------|---------|---------|-------|-----------------|")
        for a in authors:
            lines.append("| %s | %s | %s | %d | %d | %s |" % (
                a.get("name", ""),
                a.get("email", ""),
                a.get("pattern", ""),
                a.get("commit_count", 0),
                a.get("files_touched", 0),
                a.get("primary_cluster", ""),
            ))
        lines.append("")

    # Top impact commits
    impact = report.get("impact", {})
    commits = impact.get("commits", [])
    if commits:
        sorted_commits = sorted(
            commits,
            key=lambda c: c.get("structural_impact", 0),
            reverse=True,
        )[:10]
        lines.append("## Top Impact Commits")
        lines.append("")
        lines.append("| Hash | Author | Impact | Files | Message |")
        lines.append("|------|--------|--------|-------|---------|")
        for c in sorted_commits:
            lines.append("| %s | %s | %.1f | %d | %s |" % (
                c.get("hash", "")[:8],
                c.get("author_name", ""),
                c.get("structural_impact", 0),
                c.get("files_changed", 0),
                c.get("message", "")[:60],
            ))
        lines.append("")

    return "\n".join(lines)
