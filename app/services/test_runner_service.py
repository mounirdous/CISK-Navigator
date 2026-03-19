"""
Test Runner Service for executing pytest and parsing results
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


class TestRunnerService:
    """Service to run pytest and parse results"""

    @staticmethod
    def run_tests(include_coverage: bool = True, test_path: Optional[str] = None, progress_callback=None) -> Dict:
        """
        Run pytest and return structured results

        Args:
            include_coverage: Whether to run with coverage analysis
            test_path: Optional specific test path (default: all tests)
            progress_callback: Optional callback function to report progress

        Returns:
            Dict with test results, coverage, and metadata
        """
        project_root = Path(__file__).parent.parent.parent
        test_directory = project_root / "tests" if test_path is None else Path(test_path)

        # Report progress if callback provided
        if progress_callback:
            # Count test files
            test_files = list(test_directory.rglob("test_*.py"))
            progress_callback(f"Found {len(test_files)} test files, executing tests...")

        # Build pytest command
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_directory),
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            "-q",  # Quiet
        ]

        if include_coverage:
            cmd.extend(
                [
                    "--cov=app",
                    "--cov-report=term-missing",
                    "--cov-report=json",
                ]
            )

        try:
            # Run pytest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(project_root),
                timeout=300,  # 5 minute timeout
            )

            # Parse output
            output = result.stdout + result.stderr
            exit_code = result.returncode

            # Parse test results
            test_results = TestRunnerService._parse_test_output(output)

            # Parse coverage if enabled
            coverage_data = None
            if include_coverage:
                coverage_file = project_root / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file, "r") as f:
                        coverage_data = json.load(f)

            return {
                "status": "success" if exit_code == 0 else "failed",
                "exit_code": exit_code,
                "output": output,
                "test_results": test_results,
                "coverage": TestRunnerService._parse_coverage(coverage_data) if coverage_data else None,
                "summary": TestRunnerService._generate_summary(test_results, coverage_data),
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "Test execution timed out (5 minutes)",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    def _parse_test_output(output: str) -> Dict:
        """Parse pytest output to extract test results"""
        results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "total": 0,
            "duration": 0.0,
            "failed_tests": [],
            "test_files": {},
        }

        # Extract summary line (e.g., "5 passed, 2 failed in 1.23s")
        summary_pattern = (
            r"(?:(\d+) passed)?.*?(?:(\d+) failed)?.*?(?:(\d+) skipped)?.*?(?:(\d+) error)?.*?in ([\d.]+)s"
        )
        summary_match = re.search(summary_pattern, output)

        if summary_match:
            results["passed"] = int(summary_match.group(1) or 0)
            results["failed"] = int(summary_match.group(2) or 0)
            results["skipped"] = int(summary_match.group(3) or 0)
            results["errors"] = int(summary_match.group(4) or 0)
            results["duration"] = float(summary_match.group(5) or 0)
            results["total"] = results["passed"] + results["failed"] + results["skipped"] + results["errors"]

        # Extract failed test details
        failed_pattern = r"FAILED (tests/[^\s]+) - (.+?)(?:\n|$)"
        failed_matches = re.findall(failed_pattern, output)
        for test_path, error_msg in failed_matches:
            results["failed_tests"].append({"path": test_path, "error": error_msg})

        # Extract test file statistics
        file_pattern = r"(tests/\w+/test_\w+\.py)"
        test_files = re.findall(file_pattern, output)
        for file_path in set(test_files):
            file_name = Path(file_path).name
            results["test_files"][file_name] = results["test_files"].get(file_name, 0) + 1

        return results

    @staticmethod
    def _parse_coverage(coverage_data: Dict) -> Dict:
        """Parse coverage.json to extract useful metrics"""
        if not coverage_data:
            return None

        totals = coverage_data.get("totals", {})
        files = coverage_data.get("files", {})

        # Calculate per-module coverage
        modules = {}
        for file_path, file_data in files.items():
            if "app/" in file_path:
                # Extract module name (e.g., app/services/backup_service.py -> services)
                parts = file_path.split("/")
                if len(parts) >= 2:
                    module = parts[1]
                    if module not in modules:
                        modules[module] = {
                            "covered_lines": 0,
                            "total_lines": 0,
                            "missing_lines": 0,
                            "files": 0,
                        }

                    summary = file_data.get("summary", {})
                    modules[module]["covered_lines"] += summary.get("covered_lines", 0)
                    modules[module]["total_lines"] += summary.get("num_statements", 0)
                    modules[module]["missing_lines"] += summary.get("missing_lines", 0)
                    modules[module]["files"] += 1

        # Calculate percentages
        for module in modules.values():
            if module["total_lines"] > 0:
                module["percent"] = round((module["covered_lines"] / module["total_lines"]) * 100, 2)
            else:
                module["percent"] = 0

        return {
            "total_percent": round(totals.get("percent_covered", 0), 2),
            "covered_lines": totals.get("covered_lines", 0),
            "total_lines": totals.get("num_statements", 0),
            "missing_lines": totals.get("missing_lines", 0),
            "modules": modules,
        }

    @staticmethod
    def _generate_summary(test_results: Dict, coverage_data: Optional[Dict]) -> Dict:
        """Generate human-readable summary"""
        summary = {
            "status": "healthy" if test_results["failed"] == 0 and test_results["errors"] == 0 else "degraded",
            "test_status": (
                "All tests passing" if test_results["failed"] == 0 else f"{test_results['failed']} tests failing"
            ),
            "pass_rate": 0,
        }

        if test_results["total"] > 0:
            summary["pass_rate"] = round((test_results["passed"] / test_results["total"]) * 100, 2)

        if coverage_data:
            summary["coverage_status"] = f"{coverage_data['totals'].get('percent_covered', 0):.2f}% coverage"

        return summary

    @staticmethod
    def save_test_execution(results: Dict, user_id: Optional[int] = None):
        """
        Save test execution results to database

        Args:
            results: Test results dict from run_tests()
            user_id: ID of user who executed tests

        Returns:
            TestExecution model instance
        """
        from app.extensions import db
        from app.models.test_execution import TestExecution

        test_results = results.get("test_results", {})
        coverage = results.get("coverage")

        execution = TestExecution(
            executed_by_user_id=user_id,
            status=results.get("status", "error"),
            total_tests=test_results.get("total", 0),
            passed_tests=test_results.get("passed", 0),
            failed_tests=test_results.get("failed", 0),
            skipped_tests=test_results.get("skipped", 0),
            error_tests=test_results.get("errors", 0),
            duration_seconds=test_results.get("duration", 0.0),
            coverage_percent=coverage.get("total_percent") if coverage else None,
            covered_lines=coverage.get("covered_lines") if coverage else None,
            total_lines=coverage.get("total_lines") if coverage else None,
            missing_lines=coverage.get("missing_lines") if coverage else None,
            failed_test_details=test_results.get("failed_tests", []),
            coverage_by_module=coverage.get("modules") if coverage else None,
            python_version=sys.version.split()[0],
            environment=os.environ.get("FLASK_ENV", "production"),
        )

        db.session.add(execution)
        db.session.commit()

        return execution

    @staticmethod
    def get_test_history(limit: int = 30):
        """
        Get recent test execution history

        Args:
            limit: Maximum number of records to return

        Returns:
            List of TestExecution instances
        """
        from app.models.test_execution import TestExecution

        return TestExecution.query.order_by(TestExecution.executed_at.desc()).limit(limit).all()
