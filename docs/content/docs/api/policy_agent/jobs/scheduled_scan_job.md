---
sidebar_label: scheduled_scan_job
title: policy_agent.jobs.scheduled_scan_job
---

Entry point for the scheduled scan job (``policy-agent-scheduled-scan``).

Runs the same scan as the on-demand job; the Databricks Asset Bundle attaches the cron
schedule. The only difference is the recorded trigger label.

#### main

```python
def main() -> None
```

Runs the scheduled scan of every approved policy and exits with its status code.

