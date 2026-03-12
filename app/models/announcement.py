"""
System Announcement models
"""

from datetime import datetime

from app.extensions import db


class SystemAnnouncement(db.Model):
    """
    System-wide announcements/banners.

    Super admins can create announcements that display on dashboards.
    Can target all users, specific organizations, or specific users.
    """

    __tablename__ = "system_announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    banner_type = db.Column(db.String(20), nullable=False)  # info, warning, success, alert
    is_dismissible = db.Column(db.Boolean, default=True, nullable=False)
    target_type = db.Column(db.String(20), nullable=False)  # all, organizations, users
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # Relationships
    creator = db.relationship("User", foreign_keys=[created_by])
    acknowledgments = db.relationship(
        "UserAnnouncementAcknowledgment", back_populates="announcement", cascade="all, delete-orphan"
    )
    target_users = db.relationship(
        "AnnouncementTargetUser", back_populates="announcement", cascade="all, delete-orphan"
    )
    target_organizations = db.relationship(
        "AnnouncementTargetOrganization", back_populates="announcement", cascade="all, delete-orphan"
    )

    def is_visible_now(self):
        """Check if announcement should be visible based on date range"""
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return self.is_active

    def is_visible_for_user(self, user_id, org_id=None):
        """Check if announcement should be visible for a specific user"""
        if not self.is_visible_now():
            return False

        # Check targeting
        if self.target_type == "all":
            return True
        elif self.target_type == "organizations" and org_id:
            return any(target.organization_id == org_id for target in self.target_organizations)
        elif self.target_type == "users":
            # Check if user is in target list
            return any(target.user_id == user_id for target in self.target_users)

        return False

    def has_been_acknowledged_by(self, user_id):
        """Check if user has acknowledged this announcement"""
        return any(ack.user_id == user_id for ack in self.acknowledgments)

    def get_acknowledgment_count(self):
        """Get count of users who acknowledged"""
        return len(self.acknowledgments)

    def get_banner_config(self):
        """Get banner styling configuration based on type"""
        configs = {
            "info": {
                "bg": "rgba(13, 110, 253, 0.1)",
                "border": "#0d6efd",
                "icon": "bi-info-circle-fill",
                "text": "#0d6efd",
            },
            "warning": {
                "bg": "rgba(255, 193, 7, 0.1)",
                "border": "#ffc107",
                "icon": "bi-exclamation-triangle-fill",
                "text": "#ffc107",
            },
            "success": {
                "bg": "rgba(25, 135, 84, 0.1)",
                "border": "#198754",
                "icon": "bi-check-circle-fill",
                "text": "#198754",
            },
            "alert": {
                "bg": "rgba(220, 53, 69, 0.1)",
                "border": "#dc3545",
                "icon": "bi-exclamation-octagon-fill",
                "text": "#dc3545",
            },
        }
        return configs.get(self.banner_type, configs["info"])

    def __repr__(self):
        return f"<SystemAnnouncement {self.id}: {self.title}>"


class UserAnnouncementAcknowledgment(db.Model):
    """Track which users have acknowledged announcements"""

    __tablename__ = "user_announcement_acknowledgments"

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(
        db.Integer, db.ForeignKey("system_announcements.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Unique constraint
    __table_args__ = (db.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_user"),)

    # Relationships
    announcement = db.relationship("SystemAnnouncement", back_populates="acknowledgments")
    user = db.relationship("User")

    def __repr__(self):
        return f"<Acknowledgment ann_id={self.announcement_id} user_id={self.user_id}>"


class AnnouncementTargetUser(db.Model):
    """Target specific users for an announcement"""

    __tablename__ = "announcement_target_users"

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(
        db.Integer, db.ForeignKey("system_announcements.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    announcement = db.relationship("SystemAnnouncement", back_populates="target_users")
    user = db.relationship("User")

    def __repr__(self):
        return f"<AnnouncementTarget ann_id={self.announcement_id} user_id={self.user_id}>"


class AnnouncementTargetOrganization(db.Model):
    """Target specific organizations for an announcement"""

    __tablename__ = "announcement_target_organizations"

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(
        db.Integer, db.ForeignKey("system_announcements.id", ondelete="CASCADE"), nullable=False
    )
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    announcement = db.relationship("SystemAnnouncement", back_populates="target_organizations")
    organization = db.relationship("Organization")

    def __repr__(self):
        return f"<AnnouncementTargetOrg ann_id={self.announcement_id} org_id={self.organization_id}>"
