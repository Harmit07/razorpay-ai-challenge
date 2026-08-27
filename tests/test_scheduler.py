import unittest
from datetime import datetime, timezone, timedelta
from src.generators.batch_generator import BatchFailureGenerator
from src.classifiers.rule_classifier import RuleBasedClassifier
from src.router.compliance_router import ComplianceRouter
from src.scheduler.simulated_clock import (
    SimulatedClockScheduler,
    ScheduledTask,
    TaskType,
    TaskStatus,
)


class TestSimulatedClockScheduler(unittest.TestCase):
    def setUp(self):
        self.base_time = datetime(2026, 8, 27, 10, 0, tzinfo=timezone.utc)
        self.scheduler = SimulatedClockScheduler(initial_time=self.base_time)
        self.generator = BatchFailureGenerator(seed=42)
        self.classifier = RuleBasedClassifier()
        self.router = ComplianceRouter()

    def test_schedule_and_fast_forward_24h_pre_debit_sequence(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False, base_timestamp=self.base_time)
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)

        tasks = self.scheduler.schedule_action_plan(plan)
        self.assertEqual(len(tasks), 2)  # Notice task + Debit task

        # Step 1: Advance by 12 hours -> Nothing should fire yet if notice is at +24h
        pre_debit_time = plan.pre_debit_notice_dispatch_time
        debit_time = plan.scheduled_execution_time

        # Fast forward right to pre_debit_time
        fired = self.scheduler.fast_forward_to(pre_debit_time)
        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0]["task_type"], TaskType.PRE_DEBIT_ALERT_DISPATCH.value)
        self.assertEqual(self.scheduler.current_time, pre_debit_time)

        # Fast forward to debit execution time
        fired_debit = self.scheduler.fast_forward_to(debit_time)
        self.assertEqual(len(fired_debit), 1)
        self.assertEqual(fired_debit[0]["task_type"], TaskType.AUTO_DEBIT_EXECUTION.value)
        self.assertEqual(self.scheduler.current_time, debit_time)

    def test_cancel_tasks_on_early_payment(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False, base_timestamp=self.base_time)
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)

        self.scheduler.schedule_action_plan(plan)
        self.assertEqual(len(self.scheduler.get_pending_tasks(event.txn_id)), 2)

        # Customer pays immediately (STOP_PAID) -> cancel all tasks
        cancelled_count = self.scheduler.cancel_tasks_for_txn(event.txn_id, reason="STOP_PAID: Customer cleared invoice early via portal")
        self.assertEqual(cancelled_count, 2)
        self.assertEqual(len(self.scheduler.get_pending_tasks(event.txn_id)), 0)

        # Fast forward 10 days -> 0 tasks should fire
        fired = self.scheduler.step_days(10)
        self.assertEqual(len(fired), 0)

    def test_handler_registration_and_execution(self):
        executed_types = []

        def mock_handler(task: ScheduledTask, fire_time: datetime):
            executed_types.append((task.task_type, fire_time))
            return f"Processed {task.task_id}"

        self.scheduler.register_handler(TaskType.PRE_DEBIT_ALERT_DISPATCH, mock_handler)
        self.scheduler.register_handler(TaskType.AUTO_DEBIT_EXECUTION, mock_handler)

        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False, base_timestamp=self.base_time)
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)
        self.scheduler.schedule_action_plan(plan)

        # Fast forward 7 days
        self.scheduler.step_days(7)
        self.assertEqual(len(executed_types), 2)
        self.assertEqual(executed_types[0][0], TaskType.PRE_DEBIT_ALERT_DISPATCH)
        self.assertEqual(executed_types[1][0], TaskType.AUTO_DEBIT_EXECUTION)

    def test_fast_forward_full_750_batch_simulation(self):
        events = self.generator.load_from_json("data/synthetic_transactions_750.json")
        diag_results = self.classifier.classify_batch(events)
        plans = self.router.route_batch(list(zip(events, diag_results)))

        for p in plans:
            self.scheduler.schedule_action_plan(p)

        total_pending = len(self.scheduler.get_pending_tasks())
        print(f"\nSimulated-Clock Scheduler: Enqueued {total_pending} tasks across 750 transactions.")

        # Fast-forward 14 full days (14-day dunning window) in ~0.01 seconds!
        fired_events = self.scheduler.step_days(14)
        print(f"Simulated-Clock Scheduler: Fast-forwarded 14 Days -> Fired {len(fired_events)} scheduled tasks instantly!")

        self.assertGreater(len(fired_events), 500)
        self.assertEqual(len(self.scheduler._task_heap), 0)


if __name__ == "__main__":
    unittest.main()
