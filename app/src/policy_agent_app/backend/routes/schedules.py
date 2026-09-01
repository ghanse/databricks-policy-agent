"""Scan schedule endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from policy_agent.approval.roles import Role
from policy_agent.config import PolicyAgentConfig
from policy_agent.policy.model import ResourceType
from policy_agent.schedule import ScanSchedule
from policy_agent.storage.backend import (
    SqlExecutor,
    delete_schedule,
    read_schedules,
    save_schedule,
)

from policy_agent_app.backend.auth import current_user, require_admin
from policy_agent_app.backend.dependencies import get_config, get_executor
from policy_agent_app.backend.schemas import ScheduleRequest, schedule_to_dict

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("")
def list_schedules(
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> list[dict[str, Any]]:
    """List scan schedules."""
    return [schedule_to_dict(schedule) for schedule in read_schedules(executor, config.storage)]


@router.post("", status_code=status.HTTP_201_CREATED)
def upsert_schedule(
    body: ScheduleRequest,
    _roles: set[Role] = Depends(require_admin),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> dict[str, Any]:
    """Create or update a scan schedule."""
    schedule = ScanSchedule(
        schedule_id=body.schedule_id or uuid.uuid4().hex,
        name=body.name,
        cron=body.cron,
        timezone=body.timezone,
        policy_names=tuple(body.policy_names),
        resource_types=tuple(ResourceType(value) for value in body.resource_types),
        paused=body.paused,
    )
    save_schedule(executor, config.storage, schedule)
    return schedule_to_dict(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def remove_schedule(
    schedule_id: str,
    _roles: set[Role] = Depends(require_admin),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> None:
    """Delete a scan schedule by id."""
    delete_schedule(executor, config.storage, schedule_id)
