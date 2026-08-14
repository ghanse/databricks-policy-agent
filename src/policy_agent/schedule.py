"""Scan schedule model.

A :class:`ScanSchedule` records the intent to run a scan regularly. The Databricks Asset
Bundle owns the actual cron trigger for the provisioned scheduled job; schedules stored here
let the app present, pause, and scope those recurring scans.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from policy_agent.policy.model import ResourceType


@dataclass(frozen=True)
class ScanSchedule:
    """A recurring scan definition.

    Attributes:
        schedule_id: Unique identifier for the schedule.
        name: Human-readable schedule name.
        cron: Quartz cron expression describing the cadence.
        timezone: IANA timezone the cron expression is evaluated in.
        policy_names: Policies to include; empty means every approved policy.
        resource_types: Resource types to include; empty means every referenced type.
        paused: Whether the schedule is currently paused.
    """

    schedule_id: str
    name: str
    cron: str
    timezone: str = "UTC"
    policy_names: tuple[str, ...] = field(default_factory=tuple)
    resource_types: tuple[ResourceType, ...] = field(default_factory=tuple)
    paused: bool = False
