"""
Feedback Request model — bug reports and enhancement requests from users.
Visible to super admins for triage and resolution.
"""

from datetime import datetime

from app.extensions import db


class FeedbackRequest(db.Model):
    """A bug report or enhancement request submitted by any user."""

    __tablename__ = "feedback_requests"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False, default="bug", index=True)  # bug, enhancement
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="medium")  # low, medium, high, critical
    status = db.Column(db.String(20), nullable=False, default="new", index=True)  # new, in_progress, resolved, wontfix, duplicate
    page_url = db.Column(db.String(500), nullable=True, comment="URL where the feedback was submitted from")
    screenshot_data = db.Column(db.LargeBinary, nullable=True, comment="Screenshot binary data")
    screenshot_mime = db.Column(db.String(50), nullable=True)

    # Who submitted
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)

    # Admin response
    admin_notes = db.Column(db.Text, nullable=True)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    submitted_by = db.relationship("User", foreign_keys=[submitted_by_id], backref="feedback_requests")
    resolved_by = db.relationship("User", foreign_keys=[resolved_by_id])
    organization = db.relationship("Organization")

    @property
    def is_open(self):
        return self.status in ("new", "in_progress")

    @property
    def type_icon(self):
        return "bi-bug" if self.type == "bug" else "bi-lightbulb"

    @property
    def priority_color(self):
        return {"low": "#6b7280", "medium": "#f59e0b", "high": "#f97316", "critical": "#ef4444"}.get(self.priority, "#6b7280")

    @property
    def status_color(self):
        return {
            "new": "#3b82f6", "in_progress": "#f59e0b",
            "resolved": "#22c55e", "wontfix": "#6b7280", "duplicate": "#8b5cf6",
        }.get(self.status, "#6b7280")

    def __repr__(self):
        return f"<FeedbackRequest #{self.id} [{self.type}] {self.title[:30]}>"
