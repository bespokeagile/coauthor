"""CLI entry point for Bespoke Coauthor.

Usage:
    bespoke-coauthor scan <path>
    bespoke-coauthor authors [scan_id]
    bespoke-coauthor impacts [scan_id]
    bespoke-coauthor history
    bespoke-coauthor serve [--port PORT] [--host HOST]
    bespoke-coauthor mcp
    bespoke-coauthor version
"""

import argparse
import sys
import uuid
from typing import List, Optional

from . import __version__
from .formats import export_json, export_markdown
from .report import format_authors_table, format_impact_table, format_summary
from .scanner import run_scan
from .store import get_scan, list_scans, save_scan


def _cmd_scan(args: argparse.Namespace) -> int:
    """Run a full scan on the target repository."""
    target = args.path
    fmt = args.format
    output = args.output
    exclude_bots = not args.include_bots

    try:
        report = run_scan(
            target=target,
            max_commits=args.max_commits,
            max_files=args.max_files,
            exclude_bots=exclude_bots,
        )
    except ValueError as e:
        print("Error: %s" % e, file=sys.stderr)
        return 1
    except RuntimeError as e:
        print("Error: %s" % e, file=sys.stderr)
        return 1

    # Save to store
    scan_id = uuid.uuid4().hex[:12]
    try:
        save_scan(
            scan_id=scan_id,
            repo_path=report.get("target", target),
            commit_sha=report.get("commit_sha", ""),
            report=report,
        )
    except Exception as e:
        print("Warning: could not save scan: %s" % e, file=sys.stderr)

    # Format output
    if fmt == "json":
        text = export_json(report)
    elif fmt == "markdown":
        text = export_markdown(report)
    else:
        # Terminal format
        lines = []
        lines.append(format_summary(report))
        lines.append("")
        lines.append("=== Authors ===")
        lines.append(format_authors_table(report.get("authorship", {})))
        lines.append("")
        lines.append("=== Top Impact Commits ===")
        lines.append(format_impact_table(report.get("impact", {})))
        lines.append("")
        lines.append("Scan ID: %s" % scan_id)
        text = "\n".join(lines)

    if output:
        try:
            with open(output, "w") as f:
                f.write(text)
            print("Report written to %s" % output)
        except IOError as e:
            print("Error writing to %s: %s" % (output, e), file=sys.stderr)
            return 1
    else:
        print(text)

    return 0


def _cmd_authors(args: argparse.Namespace) -> int:
    """Show author table from a scan."""
    scan_id = args.scan_id
    if scan_id:
        report = get_scan(scan_id)
        if report is None:
            print("Scan not found: %s" % scan_id, file=sys.stderr)
            return 1
    else:
        scans = list_scans(limit=1)
        if not scans:
            print("No scans found. Run 'coauthor scan <path>' first.", file=sys.stderr)
            return 1
        report = get_scan(scans[0]["id"])
        if report is None:
            print("Could not load latest scan.", file=sys.stderr)
            return 1

    print(format_authors_table(report.get("authorship", {})))
    return 0


def _cmd_impacts(args: argparse.Namespace) -> int:
    """Show impact table from a scan."""
    scan_id = args.scan_id
    if scan_id:
        report = get_scan(scan_id)
        if report is None:
            print("Scan not found: %s" % scan_id, file=sys.stderr)
            return 1
    else:
        scans = list_scans(limit=1)
        if not scans:
            print("No scans found. Run 'coauthor scan <path>' first.", file=sys.stderr)
            return 1
        report = get_scan(scans[0]["id"])
        if report is None:
            print("Could not load latest scan.", file=sys.stderr)
            return 1

    print(format_impact_table(report.get("impact", {})))
    return 0


def _cmd_history(args: argparse.Namespace) -> int:
    """List past scans."""
    scans = list_scans(limit=20)
    if not scans:
        print("No scans found.")
        return 0

    # Print as table
    header = "%-14s  %-40s  %-10s  %s" % ("ID", "Repository", "Commit", "Date")
    print(header)
    print("-" * len(header))
    for s in scans:
        print("%-14s  %-40s  %-10s  %s" % (
            s["id"],
            s["repo_path"][:40],
            s["commit_sha"][:10],
            s["created_at"][:19],
        ))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """Launch the web dashboard."""
    try:
        import uvicorn
    except ImportError:
        print(
            "Web dependencies not installed. Install with:\n"
            "  pip install 'bespoke-coauthor[web]'",
            file=sys.stderr,
        )
        return 1

    # Import here to avoid requiring FastAPI for CLI usage
    from .web import app  # type: ignore[import]

    print("Starting Coauthor web dashboard on %s:%d" % (args.host, args.port))
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def _cmd_mcp(args: argparse.Namespace) -> int:
    """Start the MCP server (stdio transport)."""
    from .mcp_server import run_mcp_server
    run_mcp_server()
    return 0


def _cmd_version(args: argparse.Namespace) -> int:
    """Show version."""
    print("bespoke-coauthor %s" % __version__)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="bespoke-coauthor",
        description="Open-source code authorship analysis",
    )
    subparsers = parser.add_subparsers(dest="command")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Run full analysis on a repository")
    scan_parser.add_argument("path", help="Path to git repository")
    scan_parser.add_argument(
        "--max-commits", type=int, default=0,
        help="Maximum commits to analyze (0 = all)",
    )
    scan_parser.add_argument(
        "--max-files", type=int, default=500,
        help="Maximum files to consider",
    )
    scan_parser.add_argument(
        "--include-bots", action="store_true", default=False,
        help="Include bot commits in analysis",
    )
    scan_parser.add_argument(
        "--format", choices=["terminal", "json", "markdown"],
        default="terminal",
        help="Output format (default: terminal)",
    )
    scan_parser.add_argument(
        "--output", type=str, default="",
        help="Write output to file instead of stdout",
    )

    # authors
    authors_parser = subparsers.add_parser("authors", help="Show author table")
    authors_parser.add_argument("scan_id", nargs="?", default="", help="Scan ID (default: latest)")

    # impacts
    impacts_parser = subparsers.add_parser("impacts", help="Show impact table")
    impacts_parser.add_argument("scan_id", nargs="?", default="", help="Scan ID (default: latest)")

    # history
    subparsers.add_parser("history", help="List past scans")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Launch web dashboard")
    serve_parser.add_argument(
        "--port", type=int, default=8002,
        help="Port to listen on (default: 8002)",
    )
    serve_parser.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )

    # mcp
    subparsers.add_parser("mcp", help="Start MCP server (stdio transport)")

    # version
    subparsers.add_parser("version", help="Show version")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    dispatch = {
        "scan": _cmd_scan,
        "authors": _cmd_authors,
        "impacts": _cmd_impacts,
        "history": _cmd_history,
        "serve": _cmd_serve,
        "mcp": _cmd_mcp,
        "version": _cmd_version,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
