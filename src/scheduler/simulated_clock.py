"""
Simulated-Clock Scheduler & Chronological Event Loop for AI Revenue Recovery Agent.
Enables instant discrete-event simulation across hours/days without real-time cron or sleeps.
Handles scheduled 24h pre-debit notices, cooling interval releases, salary-cycle retries,
PTP grace expiration triggers, and instant task purging upon stopping rules.
"""

from __future__ import annotations
import heapq
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

from src.models.schema import (
    TransactionFailureEvent,
    PaymentMethod,
    TransactionType,
    TransactionCategory,
    PromiseToPayRecord,
)
from src.router.compliance_router import (
    CandidateActionPlan,
    RecoveryActionType,
    RecoveryChannel,
)
from src.orchestrator.state_machine import (
    TransactionLifecycleFSM,
    RecoveryState,
)


class TaskType(str, Enum):
    PRE_DEBIT_ALERT_DISPATCH = "PRE_DEBIT_ALERT_DISPATCH"
    AUTO_DEBIT_EXECUTION = "AUTO_DEBIT_EXECUTION"
    PAYMENT_LINK_DISPATCH = "PAYMENT_LINK_DISPATCH"
    VOICE_OUTREACH_DISPATCH = "VOICE_OUTREACH_DISPATCH"
    MSMED_ESCALATION_DISPATCH = "MSMED_ESCALATION_DISPATCH"
    PTP_GRACE_EXPIRY_CHECK = "PTP_GRACE_EXPIRY_CHECK"
    COOLING_RELEASE = "COOLING_RELEASE"
    DUNNING_CEILING_EXPIRY = "DUNNING_CEILING_EXPIRY"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class ScheduledTask(BaseModel):
    """A single scheduled unit of work bound to a virtual timestamp."""
    task_id: str
    txn_id: str
    task_type: TaskType
    scheduled_time: datetime
    status: TaskStatus = TaskStatus.PENDING
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None

    def __lt__(self, other: ScheduledTask) -> bool:
        # Enables priority queue ordering by scheduled_time
        return self.scheduled_time < other.scheduled_time


class SimulatedClockScheduler:
    """
    High-performance discrete-event scheduler driven by an arbitrary virtual clock.
    """

    def __init__(self, initial_time: Optional[datetime] = None):
        self.current_time: datetime = initial_time or datetime.now(timezone.utc)
        self._task_heap: List[ScheduledTask] = []
        self._tasks_by_id: Dict[str, ScheduledTask] = {}
        self._tasks_by_txn: Dict[str, List[str]] = {}
        self.execution_log: List[Dict[str, Any]] = []
        self._handlers: Dict[TaskType, Callable[[ScheduledTask, datetime], Any]] = {}

    def set_time(self, new_time: datetime) -> None:
        """Sets the virtual clock time."""
        if new_time < self.current_time:
            raise ValueError(f"Cannot rewind simulated clock backwards from {self.current_time} to {new_time}.")
        self.current_time = new_time

    def register_handler(self, task_type: TaskType, handler: Callable[[ScheduledTask, datetime], Any]) -> None:
        """Registers a callback handler for a specific TaskType."""
        self._handlers[task_type] = handler

    def schedule_task(
        self,
        txn_id: str,
        task_type: TaskType,
        scheduled_time: datetime,
        payload: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """Schedules a new task in the virtual priority queue."""
        task_id = f"task_{task_type.value.lower()}_{txn_id}_{len(self._tasks_by_id) + 1}"
        task = ScheduledTask(
            task_id=task_id,
            txn_id=txn_id,
            task_type=task_type,
            scheduled_time=scheduled_time,
            payload=payload or {},
            created_at=self.current_time,
        )
        heapq.heappush(self._task_heap, task)
        self._tasks_by_id[task_id] = task

        if txn_id not in self._tasks_by_txn:
            self._tasks_by_txn[txn_id] = []
        self._tasks_by_txn[txn_id].append(task_id)

        return task

    def schedule_action_plan(self, plan: CandidateActionPlan) -> List[ScheduledTask]:
        """
        Translates a CandidateActionPlan into its component scheduled tasks:
        e.g., for AUTO_DEBIT_RETRY:
        1. Pre-debit alert task at pre_debit_notice_dispatch_time (>=24h prior)
        2. Auto-debit retry task at scheduled_execution_time
        """
        scheduled_tasks: List[ScheduledTask] = []

        # 1. Schedule 24h Pre-Debit Notice if required
        if plan.requires_pre_debit_notice_24h and plan.pre_debit_notice_dispatch_time:
            t1 = self.schedule_task(
                txn_id=plan.txn_id,
                task_type=TaskType.PRE_DEBIT_ALERT_DISPATCH,
                scheduled_time=plan.pre_debit_notice_dispatch_time,
                payload={
                    "channel": plan.primary_channel.value,
                    "dlt_stream": plan.dlt_stream.value,
                    "dlt_template_id": plan.dlt_template_id,
                },
            )
            scheduled_tasks.append(t1)

        # 2. Schedule Execution Action
        if plan.action_type == RecoveryActionType.AUTO_DEBIT_RETRY:
            task_type = TaskType.AUTO_DEBIT_EXECUTION
        elif plan.action_type in [RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK, RecoveryActionType.DYNAMIC_INSTRUMENT_UPDATE_LINK, RecoveryActionType.WHATSAPP_UPI_INTENT]:
            task_type = TaskType.PAYMENT_LINK_DISPATCH
        elif plan.action_type == RecoveryActionType.VOICE_RECOVERY_CALL:
            task_type = TaskType.VOICE_OUTREACH_DISPATCH
        elif plan.action_type == RecoveryActionType.MSMED_FINANCE_ESCALATION:
            task_type = TaskType.MSMED_ESCALATION_DISPATCH
        elif plan.action_type == RecoveryActionType.PTP_HOLD_FREEZE:
            task_type = TaskType.PTP_GRACE_EXPIRY_CHECK
        else:
            task_type = TaskType.COOLING_RELEASE

        t2 = self.schedule_task(
            txn_id=plan.txn_id,
            task_type=task_type,
            scheduled_time=plan.scheduled_execution_time,
            payload={
                "action_type": plan.action_type.value,
                "channel": plan.primary_channel.value,
                "dlt_stream": plan.dlt_stream.value,
                "afa_validation_enforced": plan.afa_validation_enforced,
            },
        )
        scheduled_tasks.append(t2)

        return scheduled_tasks

    def cancel_tasks_for_txn(self, txn_id: str, reason: str) -> int:
        """
        Purges and cancels all pending tasks for a given transaction
        (Triggered on STOP_PAID, STOP_MANDATE_REVOKED, STOP_DISPUTE_FRAUD, STOP_OPT_OUT).
        """
        task_ids = self._tasks_by_txn.get(txn_id, [])
        cancelled_count = 0
        for tid in task_ids:
            task = self._tasks_by_id.get(tid)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.cancelled_reason = reason
                cancelled_count += 1
                self.execution_log.append({
                    "event": "TASK_CANCELLED",
                    "task_id": task.task_id,
                    "txn_id": txn_id,
                    "cancelled_at": self.current_time.isoformat(),
                    "reason": reason,
                })
        return cancelled_count

    def advance_time(self, delta: timedelta) -> List[Dict[str, Any]]:
        """
        Fast-forwards virtual time by `delta`, executing all due tasks in chronological order.
        """
        target_time = self.current_time + delta
        return self.fast_forward_to(target_time)

    def step_hours(self, hours: int) -> List[Dict[str, Any]]:
        """Convenience method to fast-forward by N hours."""
        return self.advance_time(timedelta(hours=hours))

    def step_days(self, days: int) -> List[Dict[str, Any]]:
        """Convenience method to fast-forward by N days."""
        return self.advance_time(timedelta(days=days))

    def fast_forward_to(self, target_time: datetime) -> List[Dict[str, Any]]:
        """
        Advances virtual clock to target_time, processing all scheduled events in exact chronological sequence.
        """
        if target_time < self.current_time:
            raise ValueError(f"Cannot fast-forward backwards in time from {self.current_time} to {target_time}.")

        executed_events: List[Dict[str, Any]] = []

        while self._task_heap and self._task_heap[0].scheduled_time <= target_time:
            task = heapq.heappop(self._task_heap)

            # Skip if cancelled while in queue
            if task.status == TaskStatus.CANCELLED:
                continue

            # Advance clock to exact task firing timestamp
            self.current_time = task.scheduled_time
            task.status = TaskStatus.EXECUTED
            task.executed_at = self.current_time

            # Invoke registered handler if present
            handler_result = None
            handler = self._handlers.get(task.task_type)
            if handler:
                handler_result = handler(task, self.current_time)

            log_entry = {
                "event": "TASK_FIRED",
                "task_id": task.task_id,
                "txn_id": task.txn_id,
                "task_type": task.task_type.value,
                "scheduled_time": task.scheduled_time.isoformat(),
                "executed_at": self.current_time.isoformat(),
                "handler_result": str(handler_result) if handler_result else None,
            }
            self.execution_log.append(log_entry)
            executed_events.append(log_entry)

        # Finally, advance clock to final target time
        self.current_time = target_time
        return executed_events

    def get_pending_tasks(self, txn_id: Optional[str] = None) -> List[ScheduledTask]:
        """Returns all currently pending tasks, optionally filtered by txn_id."""
        if txn_id:
            tids = self._tasks_by_txn.get(txn_id, [])
            return [self._tasks_by_id[tid] for tid in tids if self._tasks_by_id[tid].status == TaskStatus.PENDING]
        return [t for t in self._tasks_by_id.values() if t.status == TaskStatus.PENDING]
