"""Entry point for the scheduled scan job (``policy-agent-scheduled-scan``).

Runs the same scan as the on-demand job; the Databricks Asset Bundle attaches the cron
schedule. The only difference is the recorded trigger label.
"""

from __future__ import annotations

import sys

from policy_agent.jobs.runner import execute_scan_job


def main() -> None:
    """Runs the scheduled scan of every approved policy and exits with its status code."""
    sys.exit(execute_scan_job(triggered_by="job:scheduled"))


if __name__ == "__main__":
    main()
