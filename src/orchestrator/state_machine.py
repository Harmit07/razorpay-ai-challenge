"""
Finite State Machine (FSM) Lifecycle Engine for AI Revenue Recovery Agent.
Implements the 9-state recovery lifecycle:
DETECTED -> DIAGNOSING -> ACTION_SCHEDULED -> RETRYING -> ESCALATED -> PTP_FROZEN -> HUMAN_REVIEW -> RECOVERED / UNRECOVERABLE.
Enforces valid state transition invariants and generates immutable compliance audit trail entries.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

from src.models.schema import (
    TransactionFailureEvent,
    PaymentMethod,
    TransactionType,
    TransactionCategory,
    AttemptRecord,
    AttemptStatus,
    PromiseToPayRecord,
)
from src.classifiers.rule_classifier import (
    ClassificationResult,
    RetryabilityType,
    DLTStream,
)
from src.router.compliance_router import (
    CandidateActionPlan,
    RecoveryActionType,
    RecoveryChannel,
    ComplianceEnforcer,
    ComplianceViolationError,
)


class RecoveryState(str, Enum):
    DETECTED = "DETECTED"
    DIAGNOSING = "DIAGNOSING"
    ACTION_SCHEDULED = "ACTION_SCHEDULED"
    RETRYING = "RETRYING"
    ESCALATED = "ESCALATED"
    PTP_FROZEN = "PTP_FROZEN"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    RECOVERED = "RECOVERED"
    UNRECOVERABLE = "UNRECOVERABLE"


class InvalidStateTransitionError(RuntimeError):
    """Raised when an illegal state machine transition is attempted."""
    pass


class StateTransitionRecord(BaseModel):
    """Immutable audit record for each state machine transition."""
    transition_id: str
    from_state: RecoveryState
    to_state: RecoveryState
    timestamp: datetime
    trigger_event: str
    action_plan_id: Optional[str] = None
    stopping_rule: Optional[str] = None
    audit_reasoning: str


class AuditLogEntry(BaseModel):
    """
    Standardized regulatory compliance audit record adhering to compliance-rules.md Section 10.
    """
    audit_id: str
    timestamp: datetime
    entity_id: str  # Transaction ID / Subscription ID
    customer_masked: str
    amount_inr: float
    category: str
    communication_type: str
    afa_required: bool
    afa_status: str
    event_type: str
    channel: str
    statutory_rule_applied: str
    internal_policy_applied: str
    decision_rationale: str
    outcome_status: str
    grievance_details_included: bool = True
    active_ptp_date: Optional[datetime] = None
    stop_rule_triggered: Optional[str] = None


class TransactionLifecycleFSM:
    """
    State machine orchestrator managing the full lifecycle of a single payment failure event.
    """

    ALLOWED_TRANSITIONS: Dict[RecoveryState, List[RecoveryState]] = {
        RecoveryState.DETECTED: [
            RecoveryState.DIAGNOSING,
            RecoveryState.HUMAN_REVIEW,
            RecoveryState.UNRECOVERABLE,
        ],
        RecoveryState.DIAGNOSING: [
            RecoveryState.ACTION_SCHEDULED,
            RecoveryState.HUMAN_REVIEW,
            RecoveryState.UNRECOVERABLE,
        ],
        RecoveryState.ACTION_SCHEDULED: [
            RecoveryState.RETRYING,
            RecoveryState.PTP_FROZEN,
            RecoveryState.HUMAN_REVIEW,
            RecoveryState.UNRECOVERABLE,
            RecoveryState.RECOVERED,  # If webhook received early
        ],
        RecoveryState.RETRYING: [
            RecoveryState.RECOVERED,
            RecoveryState.ESCALATED,
            RecoveryState.ACTION_SCHEDULED,  # Re-scheduling for next attempt cycle after cooling
            RecoveryState.PTP_FROZEN,
            RecoveryState.UNRECOVERABLE,
            RecoveryState.HUMAN_REVIEW,
        ],
        RecoveryState.ESCALATED: [
            RecoveryState.RECOVERED,
            RecoveryState.PTP_FROZEN,
            RecoveryState.ACTION_SCHEDULED,  # If customer requests payment link
            RecoveryState.UNRECOVERABLE,
            RecoveryState.HUMAN_REVIEW,
        ],
        RecoveryState.PTP_FROZEN: [
            RecoveryState.RECOVERED,
            RecoveryState.RETRYING,  # PTP grace window elapsed without payment -> resume retry
            RecoveryState.ESCALATED,  # PTP broken -> resume high-touch voice/WhatsApp outreach
            RecoveryState.UNRECOVERABLE,
            RecoveryState.HUMAN_REVIEW,
        ],
        RecoveryState.HUMAN_REVIEW: [
            RecoveryState.ACTION_SCHEDULED,  # Operator overrides/approves recovery plan
            RecoveryState.RECOVERED,
            RecoveryState.UNRECOVERABLE,
        ],
        RecoveryState.RECOVERED: [],  # Terminal State
        RecoveryState.UNRECOVERABLE: [],  # Terminal State
    }

    def __init__(self, event: TransactionFailureEvent):
        self.event = event
        self.current_state: RecoveryState = RecoveryState.DETECTED
        self.history: List[StateTransitionRecord] = []
        self.audit_trail: List[AuditLogEntry] = []
        self.current_action_plan: Optional[CandidateActionPlan] = None
        self.classification_result: Optional[ClassificationResult] = None
        self.ptp_record: Optional[PromiseToPayRecord] = event.ptp_record

    def _record_transition(
        self,
        to_state: RecoveryState,
        trigger_event: str,
        reasoning: str,
        stopping_rule: Optional[str] = None,
        action_plan_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> None:
        """Helper to validate and log state transitions."""
        if now is None:
            now = datetime.now(timezone.utc)

        if to_state not in self.ALLOWED_TRANSITIONS.get(self.current_state, []):
            raise InvalidStateTransitionError(
                f"Illegal state transition: Cannot transition from {self.current_state} to {to_state}."
            )

        from_state = self.current_state
        self.current_state = to_state

        rec = StateTransitionRecord(
            transition_id=f"tr_{from_state.value[:3].lower()}_{to_state.value[:3].lower()}_{len(self.history)+1}",
            from_state=from_state,
            to_state=to_state,
            timestamp=now,
            trigger_event=trigger_event,
            action_plan_id=action_plan_id,
            stopping_rule=stopping_rule,
            audit_reasoning=reasoning,
        )
        self.history.append(rec)

    # -------------------------------------------------------------------------
    # Transition 1: DETECTED -> DIAGNOSING
    # -------------------------------------------------------------------------
    def transition_to_diagnosing(self, now: Optional[datetime] = None) -> None:
        """Initiates diagnostic classification."""
        self._record_transition(
            to_state=RecoveryState.DIAGNOSING,
            trigger_event="PAYMENT_FAILURE_INGESTED",
            reasoning=f"Payment failure ingested: {self.event.error_reason}. Routing to diagnostic rule engine & LLM parser.",
            now=now,
        )

    # -------------------------------------------------------------------------
    # Transition 2: DIAGNOSING -> ACTION_SCHEDULED
    # -------------------------------------------------------------------------
    def transition_to_action_scheduled(
        self,
        plan: CandidateActionPlan,
        diag: ClassificationResult,
        now: Optional[datetime] = None,
    ) -> None:
        """Schedules compliant candidate action plan."""
        # Enforce compliance invariance check
        ComplianceEnforcer.validate(plan, self.event)
        self.current_action_plan = plan
        self.classification_result = diag

        # Determine regulatory afa_status
        if plan.afa_validation_enforced:
            afa_status = "AFA_REQUIRED_LINK_SENT"
        elif self.event.is_afa_exempt:
            afa_status = "EXEMPT_CATEGORY_SIP_INS_CC"
        else:
            afa_status = "NOT_REQUIRED"

        self._record_transition(
            to_state=RecoveryState.ACTION_SCHEDULED,
            trigger_event=f"ACTION_PLAN_GENERATED_{plan.action_type.value}",
            reasoning=plan.compliance_audit_reasoning,
            action_plan_id=f"plan_{plan.action_type.value.lower()}_{self.event.txn_id}",
            now=now,
        )

        # Emit standard regulatory audit record
        audit_entry = AuditLogEntry(
            audit_id=f"aud_{self.event.txn_id}_{len(self.audit_trail)+1}",
            timestamp=now or datetime.now(timezone.utc),
            entity_id=self.event.txn_id,
            customer_masked=self.event.customer_phone_masked or "+91-98******0000",
            amount_inr=self.event.amount,
            category=self.event.category.value,
            communication_type=plan.dlt_stream.value,
            afa_required=plan.afa_validation_enforced,
            afa_status=afa_status,
            event_type=f"{plan.action_type.value}_SCHEDULED",
            channel=plan.primary_channel.value,
            statutory_rule_applied=diag.statutory_rule_applied,
            internal_policy_applied=diag.internal_policy_applied,
            decision_rationale=plan.compliance_audit_reasoning,
            outcome_status="SCHEDULED",
            grievance_details_included=True,
            active_ptp_date=self.ptp_record.promised_date if self.ptp_record else None,
            stop_rule_triggered=plan.stopping_rule,
        )
        self.audit_trail.append(audit_entry)

    # -------------------------------------------------------------------------
    # Transition 3: ACTION_SCHEDULED -> RETRYING
    # -------------------------------------------------------------------------
    def transition_to_retrying(
        self,
        attempt_number: int,
        channel: RecoveryChannel,
        now: Optional[datetime] = None,
    ) -> None:
        """Executes auto-debit or dynamic payment link dispatch."""
        if self.event.current_attempt_count >= 3:
            raise ComplianceViolationError("VIOLATION_MAX_RETRIES_EXCEEDED: Cannot transition to RETRYING when attempt count >= 3.")

        if self.ptp_record and self.ptp_record.status == "ACTIVE":
            if (now or datetime.now(timezone.utc)) < self.ptp_record.grace_until:
                raise ComplianceViolationError("VIOLATION_PTP_FREEZE_BREACH: Cannot transition to RETRYING during active PTP grace window.")

        self._record_transition(
            to_state=RecoveryState.RETRYING,
            trigger_event=f"EXECUTE_RETRY_ATTEMPT_{attempt_number}",
            reasoning=f"Executing recovery attempt #{attempt_number} via {channel.value}.",
            now=now,
        )

    # -------------------------------------------------------------------------
    # Transition 4: RETRYING -> ESCALATED
    # -------------------------------------------------------------------------
    def transition_to_escalated(
        self,
        channel: RecoveryChannel,
        reason: str,
        now: Optional[datetime] = None,
    ) -> None:
        """Escalates to multi-channel recovery ladder (WhatsApp nudge or Voice Bot)."""
        self._record_transition(
            to_state=RecoveryState.ESCALATED,
            trigger_event=f"ESCALATE_TO_{channel.value}",
            reasoning=reason,
            now=now,
        )

    # -------------------------------------------------------------------------
    # Transition 5: RETRYING / ESCALATED -> PTP_FROZEN
    # -------------------------------------------------------------------------
    def transition_to_ptp_frozen(
        self,
        ptp_record: PromiseToPayRecord,
        now: Optional[datetime] = None,
    ) -> None:
        """Freezes all active dunning upon customer promise-to-pay commitment."""
        self.ptp_record = ptp_record
        self._record_transition(
            to_state=RecoveryState.PTP_FROZEN,
            trigger_event="CUSTOMER_PTP_PROMISED",
            reasoning=f"Promise-to-Pay recorded for {ptp_record.promised_date.isoformat()} (Amount: ₹{ptp_record.promised_amount:,.2f}). All automated outreach frozen until grace expiry {ptp_record.grace_until.isoformat()}.",
            stopping_rule="STOP_PTP_ACTIVE",
            now=now,
        )

    # -------------------------------------------------------------------------
    # Transition 6: ANY -> HUMAN_REVIEW
    # -------------------------------------------------------------------------
    def transition_to_human_review(self, reason: str, now: Optional[datetime] = None) -> None:
        """Quarantines transaction to human operators due to fraud risk or ambiguity."""
        self._record_transition(
            to_state=RecoveryState.HUMAN_REVIEW,
            trigger_event="ESCALATE_TO_HUMAN_OPS",
            reasoning=reason,
            now=now,
        )

    # -------------------------------------------------------------------------
    # Transition 7: ANY -> RECOVERED (Terminal Success)
    # -------------------------------------------------------------------------
    def transition_to_recovered(
        self,
        payment_ref: str,
        settled_amount: float,
        now: Optional[datetime] = None,
    ) -> None:
        """Marks transaction as successfully recovered."""
        self._record_transition(
            to_state=RecoveryState.RECOVERED,
            trigger_event="WEBHOOK_PAYMENT_CAPTURED",
            reasoning=f"Payment successfully captured and settled (Ref: {payment_ref}, Amount: ₹{settled_amount:,.2f}). Recovery workflow completed.",
            stopping_rule="STOP_PAID",
            now=now,
        )

    # -------------------------------------------------------------------------
    # Transition 8: ANY -> UNRECOVERABLE (Terminal Cease)
    # -------------------------------------------------------------------------
    def transition_to_unrecoverable(
        self,
        stopping_rule: str,
        reason: str,
        now: Optional[datetime] = None,
    ) -> None:
        """Terminates dunning permanently adhering to stopping rules."""
        self._record_transition(
            to_state=RecoveryState.UNRECOVERABLE,
            trigger_event=f"STOPPING_RULE_TRIGGERED_{stopping_rule}",
            reasoning=reason,
            stopping_rule=stopping_rule,
            now=now,
        )
