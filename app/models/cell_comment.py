"""
Cell Comment Model

Discussion threads and collaboration on KPI cells with @mention support.
"""
from datetime import datetime
from app.extensions import db


class CellComment(db.Model):
    """
    Comment/discussion on a KPI cell.

    Supports threading (replies), @mentions, and resolution tracking.
    """
    __tablename__ = 'cell_comments'

    id = db.Column(db.Integer, primary_key=True)

    # Link to KPI cell
    kpi_value_type_config_id = db.Column(
        db.Integer,
        db.ForeignKey('kpi_value_type_configs.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Comment metadata
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Threading support
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('cell_comments.id'), nullable=True)

    # Resolution tracking
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    # Mention tracking (denormalized for performance)
    mentioned_user_ids = db.Column(db.JSON)  # Array of user IDs mentioned in this comment

    # Relationships
    config = db.relationship('KPIValueTypeConfig', backref='comments')
    user = db.relationship('User', foreign_keys=[user_id], backref='comments_authored')
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_user_id], backref='comments_resolved')

    # Self-referential for threading
    parent = db.relationship('CellComment', remote_side=[id], backref='replies')

    # Indexes
    __table_args__ = (
        db.Index('idx_comment_config', 'kpi_value_type_config_id'),
        db.Index('idx_comment_user', 'user_id'),
        db.Index('idx_comment_parent', 'parent_comment_id'),
    )

    def __repr__(self):
        return f'<CellComment {self.id} by {self.user.display_name if self.user else "unknown"}>'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'kpi_value_type_config_id': self.kpi_value_type_config_id,
            'user_id': self.user_id,
            'user_name': self.user.display_name if self.user else 'Unknown',
            'user_login': self.user.login if self.user else '',
            'comment_text': self.comment_text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'parent_comment_id': self.parent_comment_id,
            'is_resolved': self.is_resolved,
            'resolved_by': self.resolved_by.display_name if self.resolved_by else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'mentioned_user_ids': self.mentioned_user_ids or [],
            'reply_count': len(self.replies) if self.replies else 0,
        }

    def get_thread(self):
        """Get this comment and all its replies"""
        thread = [self]
        for reply in self.replies:
            thread.extend(reply.get_thread())
        return thread


class MentionNotification(db.Model):
    """
    Track @mentions for notification purposes.

    Created when a user is mentioned in a comment.
    """
    __tablename__ = 'mention_notifications'

    id = db.Column(db.Integer, primary_key=True)

    # Who was mentioned
    mentioned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Where they were mentioned
    comment_id = db.Column(db.Integer, db.ForeignKey('cell_comments.id', ondelete='CASCADE'), nullable=False)

    # Notification status
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    mentioned_user = db.relationship('User', backref='mention_notifications')
    comment = db.relationship('CellComment', backref='mention_notifications')

    def __repr__(self):
        return f'<MentionNotification {self.id} for user {self.mentioned_user_id}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'mentioned_user_id': self.mentioned_user_id,
            'comment_id': self.comment_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'comment': self.comment.to_dict() if self.comment else None,
        }
