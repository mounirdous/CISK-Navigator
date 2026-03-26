"""
Benchmark models for performance tracking.
"""

from datetime import datetime

from app.extensions import db


class BenchmarkRun(db.Model):
    """A single benchmark run with metadata."""
    __tablename__ = "benchmark_runs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=True)
    iterations = db.Column(db.Integer, default=5)

    # Snapshot of org size at time of run
    count_spaces = db.Column(db.Integer, default=0)
    count_challenges = db.Column(db.Integer, default=0)
    count_initiatives = db.Column(db.Integer, default=0)
    count_systems = db.Column(db.Integer, default=0)
    count_kpis = db.Column(db.Integer, default=0)
    count_value_types = db.Column(db.Integer, default=0)

    # Relationships
    results = db.relationship("BenchmarkResult", backref="run", cascade="all, delete-orphan", lazy="dynamic")
    creator = db.relationship("User", foreign_keys=[created_by])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.creator.display_name if self.creator else None,
            "iterations": self.iterations,
            "organization_id": self.organization_id,
            "count_spaces": self.count_spaces,
            "count_challenges": self.count_challenges,
            "count_initiatives": self.count_initiatives,
            "count_systems": self.count_systems,
            "count_kpis": self.count_kpis,
            "count_value_types": self.count_value_types,
            "results": [r.to_dict() for r in self.results],
        }


class BenchmarkResult(db.Model):
    """Individual metric result within a benchmark run."""
    __tablename__ = "benchmark_results"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("benchmark_runs.id"), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False)
    min_ms = db.Column(db.Float, default=0)
    avg_ms = db.Column(db.Float, default=0)
    max_ms = db.Column(db.Float, default=0)
    median_ms = db.Column(db.Float, default=0)
    p95_ms = db.Column(db.Float, default=0)
    raw_values = db.Column(db.JSON, nullable=True)  # Array of individual timings

    def to_dict(self):
        return {
            "metric_name": self.metric_name,
            "min_ms": round(self.min_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "median_ms": round(self.median_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "raw_values": self.raw_values,
        }
