"""Entry point for the on-demand scan job (``policy-agent-scan``)."""

from __future__ import annotations

import sys

from policy_agent.jobs.runner import execute_scan_job


def main() -> None:
    """Runs an on-demand scan of every approved policy and exits with its status code."""
    sys.exit(execute_scan_job(triggered_by="job:scan"))


if __name__ == "__main__":
    main()
