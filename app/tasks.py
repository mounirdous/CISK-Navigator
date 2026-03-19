"""
Celery background tasks
"""

from app import celery
from app.services.test_runner_service import TestRunnerService


@celery.task(bind=True, name="app.tasks.run_test_suite")
def run_test_suite_task(self, user_id=None):
    """
    Background task to run pytest test suite with coverage

    Args:
        user_id: ID of user who triggered the test run

    Returns:
        Dict with test results and coverage data
    """
    # Update progress: Starting
    self.update_state(state="PROGRESS", meta={"status": "Discovering test files...", "step": 1})

    # Create progress callback
    def update_progress(message, step=2):
        self.update_state(state="PROGRESS", meta={"status": message, "step": step})

    # Run the tests
    results = TestRunnerService.run_tests(include_coverage=True, progress_callback=update_progress)

    # Update progress: Processing results
    test_results = results.get("test_results", {})
    total_tests = test_results.get("total", 0)
    passed = test_results.get("passed", 0)
    failed = test_results.get("failed", 0)

    update_progress(f"Completed: {passed} passed, {failed} failed out of {total_tests} tests", step=3)

    # Save to database if successful
    if results.get("status") != "error":
        TestRunnerService.save_test_execution(results, user_id=user_id)

    return results
