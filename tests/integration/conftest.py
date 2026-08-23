"""Integration-test configuration.

These tests require a live Databricks workspace and are marked ``integration``. The Databricks
Labs pytester plugin — registered automatically as a pytest entry point — supplies the ``ws``,
``make_job``, ``make_cluster``, ``make_warehouse``, ``make_schema``, and ``make_random``
fixtures, and tears down everything it creates.

Authentication uses the standard Databricks SDK environment. Locally, the ambient CLI profile
works; in CI the workspace host and a service principal are provided via environment variables
(``DATABRICKS_HOST``, ``DATABRICKS_CLIENT_ID``, ``DATABRICKS_CLIENT_SECRET`` for OAuth M2M). The
Delta storage tests additionally require ``POLICY_AGENT_WAREHOUSE_ID`` and skip without it.
"""
