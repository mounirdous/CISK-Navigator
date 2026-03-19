"""
Test Execution History Model
Stores test run results for trend analysis
"""

from datetime import datetime

from app.extensions import db


class TestExecution(db.Model):
    """Store test execution results for history and trends"""

    __tablename__ = "test_executions"

    id = db.Column(db.Integer, primary_key=True)
    executed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    executed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Test Results
    status = db.Column(db.String(20), nullable=False)  # success, failed, timeout, error
    total_tests = db.Column(db.Integer, default=0)
    passed_tests = db.Column(db.Integer, default=0)
    failed_tests = db.Column(db.Integer, default=0)
    skipped_tests = db.Column(db.Integer, default=0)
    error_tests = db.Column(db.Integer, default=0)
    duration_seconds = db.Column(db.Float, default=0.0)

    # Coverage Data
    coverage_percent = db.Column(db.Float, nullable=True)
    covered_lines = db.Column(db.Integer, nullable=True)
    total_lines = db.Column(db.Integer, nullable=True)
    missing_lines = db.Column(db.Integer, nullable=True)

    # Detailed Results (JSON)
    failed_test_details = db.Column(db.JSON, nullable=True)  # List of failed test info
    coverage_by_module = db.Column(db.JSON, nullable=True)  # Module-level coverage breakdown

    # Environment Info
    python_version = db.Column(db.String(50), nullable=True)
    environment = db.Column(db.String(50), nullable=True)

    # Relationships
    executed_by = db.relationship("User", backref="test_executions")

    def __repr__(self):
        return f"<TestExecution {self.id} - {self.status} - {self.executed_at}>"

    @property
    def pass_rate(self):
        """Calculate pass rate percentage"""
        if self.total_tests > 0:
            return round((self.passed_tests / self.total_tests) * 100, 2)
        return 0

    @property
    def is_healthy(self):
        """Check if test run is considered healthy"""
        return self.status == "success" and self.failed_tests == 0 and self.error_tests == 0
