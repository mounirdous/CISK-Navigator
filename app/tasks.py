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
    # Update task state to show progress
    self.update_state(state="PROGRESS", meta={"status": "Executing tests..."})

    # Run the tests
    results = TestRunnerService.run_tests(include_coverage=True)

    # Save to database if successful
    if results.get("status") != "error":
        TestRunnerService.save_test_execution(results, user_id=user_id)

    return results
