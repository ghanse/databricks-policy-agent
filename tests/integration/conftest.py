"""Integration-test configuration.

These tests require a live Databricks workspace (authenticated via the ambient Databricks
CLI profile / SDK config) and are marked ``integration``. The Databricks Labs pytester
plugin — registered automatically as a pytest entry point — supplies the ``ws``,
``make_job``, ``make_schema``, and ``make_random`` fixtures.
"""
