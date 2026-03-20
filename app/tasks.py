"""
Celery background tasks
"""

from app import celery
from app.services.test_runner_service import TestRunnerService


@celery.task(bind=True, name="app.tasks.run_test_suite")
def run_test_suite_task(self, user_id=None, test_path=None):
    """
    Background task to run pytest test suite with coverage

    Args:
        user_id: ID of user who triggered the test run

    Returns:
        Dict with test results and coverage data
    """
    # Update progress: Starting
    self.update_state(state="PROGRESS", meta={"status": "Discovering test files...", "step": 1, "passed": 0, "failed": 0, "total": 0})

    # Create progress callback
    def update_progress(message, step=2, passed=0, failed=0, total=0):
        self.update_state(state="PROGRESS", meta={"status": message, "step": step, "passed": passed, "failed": failed, "total": total})

    # Run the tests
    results = TestRunnerService.run_tests(include_coverage=(test_path is None), test_path=test_path, progress_callback=update_progress)

    # Update progress: Processing results
    test_results = results.get("test_results", {})
    total_tests = test_results.get("total", 0)
    passed = test_results.get("passed", 0)
    failed = test_results.get("failed", 0)

    update_progress(f"Completed: {passed} passed, {failed} failed out of {total_tests} tests", step=3, passed=passed, failed=failed, total=total_tests)

    # Save to database if successful
    if results.get("status") != "error":
        try:
            TestRunnerService.save_test_execution(results, user_id=user_id)
        except Exception as e:
            print(f"Warning: Could not save test execution to DB: {e}")

    return results
