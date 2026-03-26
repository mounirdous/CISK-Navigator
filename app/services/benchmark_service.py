"""
Benchmark service for measuring database and server performance.
"""

import statistics
import time

from app.extensions import db
from app.models import (
    BenchmarkResult,
    BenchmarkRun,
    Challenge,
    Initiative,
    KPI,
    Organization,
    Space,
    System,
    ValueType,
)


class BenchmarkService:
    """Service for running performance benchmarks."""

    # Metric definitions
    METRICS = {
        "db_entity_count": {
            "label": "DB: Entity Count Queries",
            "description": "Count all entity tables (spaces, challenges, initiatives, systems, KPIs)",
            "category": "database",
        },
        "db_full_hierarchy": {
            "label": "DB: Full Hierarchy Load",
            "description": "Load complete org hierarchy with all joins",
            "category": "database",
        },
        "db_value_types": {
            "label": "DB: Value Types Query",
            "description": "Load all value types with configurations",
            "category": "database",
        },
        "server_get_data": {
            "label": "Server: Workspace get_data",
            "description": "Full workspace API data assembly (the heavy endpoint)",
            "category": "server",
        },
    }

    @staticmethod
    def _time_ms(func):
        """Run a function and return execution time in milliseconds."""
        start = time.perf_counter()
        func()
        return (time.perf_counter() - start) * 1000

    @staticmethod
    def _calc_stats(values):
        """Calculate min, avg, max, median, p95 from a list of values."""
        if not values:
            return 0, 0, 0, 0, 0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        p95_idx = min(int(n * 0.95), n - 1)
        return (
            min(sorted_vals),
            statistics.mean(sorted_vals),
            max(sorted_vals),
            statistics.median(sorted_vals),
            sorted_vals[p95_idx],
        )

    @staticmethod
    def _bench_db_entity_count(org_id):
        """Benchmark: count all entity tables."""
        from app.models import InitiativeSystemLink

        Space.query.filter_by(organization_id=org_id).count()
        Challenge.query.filter_by(organization_id=org_id).count()
        Initiative.query.filter_by(organization_id=org_id).count()
        System.query.filter_by(organization_id=org_id).count()
        db.session.query(db.func.count(KPI.id)).join(
            InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id
        ).join(System, InitiativeSystemLink.system_id == System.id).filter(
            System.organization_id == org_id
        ).scalar()
        ValueType.query.filter_by(organization_id=org_id).count()

    @staticmethod
    def _bench_db_full_hierarchy(org_id):
        """Benchmark: load full hierarchy via link tables."""
        spaces = Space.query.filter_by(organization_id=org_id).all()
        for space in spaces:
            for challenge in space.challenges:
                for ci_link in challenge.initiative_links:
                    initiative = ci_link.initiative
                    for is_link in initiative.system_links:
                        _ = is_link.system
                        _ = is_link.kpis

    @staticmethod
    def _bench_db_value_types(org_id):
        """Benchmark: load all value types."""
        ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    @staticmethod
    def _bench_server_get_data(org_id, app):
        """Benchmark: simulate the workspace get_data endpoint."""
        with app.test_client() as client:
            # We need to simulate a logged-in session
            # Instead, just call the service layer directly
            from app.routes.workspace import get_data_json
            get_data_json(org_id)

    @staticmethod
    def get_org_counts(org_id):
        """Get current entity counts for an organization."""
        from app.models import InitiativeSystemLink

        kpi_count = (
            db.session.query(db.func.count(KPI.id))
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(System, InitiativeSystemLink.system_id == System.id)
            .filter(System.organization_id == org_id)
            .scalar()
        ) or 0

        return {
            "count_spaces": Space.query.filter_by(organization_id=org_id).count(),
            "count_challenges": Challenge.query.filter_by(organization_id=org_id).count(),
            "count_initiatives": Initiative.query.filter_by(organization_id=org_id).count(),
            "count_systems": System.query.filter_by(organization_id=org_id).count(),
            "count_kpis": kpi_count,
            "count_value_types": ValueType.query.filter_by(organization_id=org_id, is_active=True).count(),
        }

    @classmethod
    def run_benchmarks(cls, name, description, org_id, user_id, iterations=5, app=None):
        """
        Run all benchmark metrics and save results.
        Returns the BenchmarkRun object.
        """
        # Get current org counts
        counts = cls.get_org_counts(org_id)

        # Create the run record
        run = BenchmarkRun(
            name=name,
            description=description,
            organization_id=org_id,
            created_by=user_id,
            iterations=iterations,
            **counts,
        )
        db.session.add(run)
        db.session.flush()

        # Define benchmark functions
        benchmarks = {
            "db_entity_count": lambda: cls._bench_db_entity_count(org_id),
            "db_full_hierarchy": lambda: cls._bench_db_full_hierarchy(org_id),
            "db_value_types": lambda: cls._bench_db_value_types(org_id),
        }

        # Try to add server benchmark if we can access workspace internals
        try:
            from app.routes.workspace import get_data_json
            benchmarks["server_get_data"] = lambda: get_data_json(org_id)
        except ImportError:
            pass

        # Run each benchmark
        for metric_name, bench_func in benchmarks.items():
            values = []
            for _ in range(iterations):
                ms = cls._time_ms(bench_func)
                values.append(round(ms, 2))
                # Clear SQLAlchemy session cache between iterations for fair measurement
                db.session.expire_all()

            min_ms, avg_ms, max_ms, median_ms, p95_ms = cls._calc_stats(values)

            result = BenchmarkResult(
                run_id=run.id,
                metric_name=metric_name,
                min_ms=min_ms,
                avg_ms=avg_ms,
                max_ms=max_ms,
                median_ms=median_ms,
                p95_ms=p95_ms,
                raw_values=values,
            )
            db.session.add(result)

        db.session.commit()
        return run
