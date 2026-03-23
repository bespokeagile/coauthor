"""Terminal output formatting.

Formats scan results as human-readable text tables for CLI display.
No external dependencies.
"""

from typing import Dict


def format_authors_table(authorship: Dict) -> str:
    """Format authors as a text table.

    Columns: Name, Email, Pattern, Commits, Clusters, Primary
    """
    authors = authorship.get("authors", [])
    if not authors:
        return "No authors found."

    # Column headers
    headers = ["Name", "Email", "Pattern", "Commits", "Clusters", "Primary"]
    # Column widths (minimum based on headers)
    widths = [len(h) for h in headers]

    # Compute max widths from data
    rows = []
    for a in authors:
        row = [
            a.get("name", ""),
            a.get("email", ""),
            a.get("pattern", ""),
            str(a.get("commit_count", 0)),
            str(len(a.get("clusters", {}))),
            a.get("primary_cluster", ""),
        ]
        rows.append(row)
        for i, val in enumerate(row):
            if len(val) > widths[i]:
                widths[i] = min(len(val), 40)  # cap at 40 chars

    # Build table
    lines = []

    # Header
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("  ".join("-" * widths[i] for i in range(len(headers))))

    # Data rows
    for row in rows:
        cells = []
        for i, val in enumerate(row):
            truncated = val[:widths[i]] if len(val) > widths[i] else val
            cells.append(truncated.ljust(widths[i]))
        lines.append("  ".join(cells))

    return "\n".join(lines)


def format_impact_table(impact: Dict) -> str:
    """Format top 10 commits by structural impact."""
    commits = impact.get("commits", [])
    if not commits:
        return "No commits found."

    # Sort by impact descending
    sorted_commits = sorted(
        commits,
        key=lambda c: c.get("structural_impact", 0),
        reverse=True,
    )[:10]

    headers = ["Hash", "Author", "Impact", "Files", "Clusters", "Message"]
    widths = [8, 20, 8, 5, 8, 50]

    lines = []
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("  ".join("-" * widths[i] for i in range(len(headers))))

    for c in sorted_commits:
        row = [
            c.get("hash", "")[:8],
            c.get("author_name", "")[:20],
            "%.1f" % c.get("structural_impact", 0),
            str(c.get("files_changed", 0)),
            str(c.get("clusters_touched", 0)),
            c.get("message", "")[:50],
        ]
        line = "  ".join(row[i].ljust(widths[i]) for i in range(len(row)))
        lines.append(line)

    return "\n".join(lines)


def format_summary(report: Dict) -> str:
    """Format a one-paragraph summary of the scan."""
    summary = report.get("summary", {})
    target = report.get("target", "unknown")

    total_authors = summary.get("total_authors", 0)
    total_commits = summary.get("total_commits", 0)
    specialists = summary.get("specialists", 0)
    generalists = summary.get("generalists", 0)
    hubs = summary.get("hubs", 0)
    top_contributor = summary.get("top_contributor", "unknown")

    parts = [
        "Repository: %s" % target,
        "Analyzed %d commits from %d authors." % (total_commits, total_authors),
        "Team composition: %d specialists, %d generalists, %d hubs." % (
            specialists, generalists, hubs
        ),
        "Top contributor: %s." % top_contributor,
    ]

    highest = summary.get("highest_impact_commit", "")
    if highest:
        parts.append("Highest impact commit: %s." % highest[:8])

    return " ".join(parts)
