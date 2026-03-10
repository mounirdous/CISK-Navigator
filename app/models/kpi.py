"""
KPI model
"""

from datetime import datetime

from sqlalchemy import func

from app.extensions import db


class KPI(db.Model):
    """
    KPI model.

    A KPI belongs to one specific Initiative-System Link.
    This allows the same system to have different KPI sets in different initiatives.

    A KPI can have multiple value types configured via KPIValueTypeConfig.
    """

    __tablename__ = "kpis"

    id = db.Column(db.Integer, primary_key=True)
    initiative_system_link_id = db.Column(
        db.Integer, db.ForeignKey("initiative_system_links.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    archived_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    initiative_system_link = db.relationship("InitiativeSystemLink", back_populates="kpis")
    value_type_configs = db.relationship("KPIValueTypeConfig", back_populates="kpi", cascade="all, delete-orphan")
    governance_body_links = db.relationship("KPIGovernanceBodyLink", back_populates="kpi", cascade="all, delete-orphan")
    archived_by = db.relationship("User", foreign_keys=[archived_by_user_id])

    def __repr__(self):
        return f"<KPI {self.name}>"

    def get_status(self):
        """
        Calculate traffic light status for this KPI.

        Returns: dict with:
            - status: "green", "yellow", or "red"
            - reason: text explanation
            - details: additional context (days_since_last_activity, target_achievement, etc.)
        """
        from app.models import Contribution

        # CRITICAL: Archived KPIs are always RED
        if self.is_archived:
            return {
                "status": "red",
                "reason": "KPI is archived",
                "details": {
                    "archived_at": self.archived_at.isoformat() if self.archived_at else None,
                    "target_achievement_pct": None,
                },
            }

        # Get all contributions for this KPI (across all value types)
        latest_contribution = (
            db.session.query(Contribution)
            .join(Contribution.kpi_value_type_config)
            .filter(Contribution.kpi_value_type_config.has(kpi_id=self.id))
            .order_by(Contribution.created_at.desc())
            .first()
        )

        # Calculate days since last activity
        if latest_contribution:
            days_since_activity = (datetime.utcnow() - latest_contribution.created_at).days
        else:
            days_since_activity = None  # No activity ever

        # Count total contributions (for consensus check)
        total_contributions = (
            db.session.query(func.count(Contribution.id))
            .join(Contribution.kpi_value_type_config)
            .filter(Contribution.kpi_value_type_config.has(kpi_id=self.id))
            .scalar()
        )

        # Check if any config has a target
        has_target = any(config.target_value is not None for config in self.value_type_configs)

        # Calculate target achievement if applicable
        target_achievement_pct = None
        target_date_status = None  # "overdue", "approaching", "ok", or None
        if has_target:
            target_achievement_pct = self._calculate_target_achievement()
            target_date_status = self._check_target_date_status()

        # === DECISION LOGIC ===

        # RED: Target date passed and not achieved (CRITICAL!)
        if target_date_status == "overdue" and target_achievement_pct and target_achievement_pct < 100:
            return {
                "status": "red",
                "reason": f"Target deadline passed - only {target_achievement_pct:.0f}% achieved",
                "details": {
                    "days_since_activity": days_since_activity,
                    "target_achievement_pct": round(target_achievement_pct, 1),
                    "target_status": "overdue",
                },
            }

        # RED: No activity ever
        if days_since_activity is None:
            return {
                "status": "red",
                "reason": "No contributions yet",
                "details": {
                    "days_since_activity": None,
                    "total_contributions": 0,
                    "target_achievement_pct": None,
                },
            }

        # RED: Stale (no activity in 30+ days)
        if days_since_activity >= 30:
            return {
                "status": "red",
                "reason": f"No activity for {days_since_activity} days",
                "details": {
                    "days_since_activity": days_since_activity,
                    "total_contributions": total_contributions,
                    "target_achievement_pct": round(target_achievement_pct, 1) if target_achievement_pct else None,
                },
            }

        # RED: Has target but achieving < 60%
        if target_achievement_pct is not None and target_achievement_pct < 60:
            return {
                "status": "red",
                "reason": f"Only {target_achievement_pct:.0f}% of target achieved",
                "details": {
                    "days_since_activity": days_since_activity,
                    "target_achievement_pct": round(target_achievement_pct, 1),
                },
            }

        # GREEN OVERRIDE: Excellent target achievement (≥90%) overrides other concerns
        if target_achievement_pct is not None and target_achievement_pct >= 90:
            return {
                "status": "green",
                "reason": f"Excellent target achievement ({target_achievement_pct:.0f}%)",
                "details": {
                    "days_since_activity": days_since_activity,
                    "total_contributions": total_contributions,
                    "target_achievement_pct": round(target_achievement_pct, 1),
                },
            }

        # YELLOW: Low activity (14-29 days)
        if days_since_activity >= 14:
            return {
                "status": "yellow",
                "reason": f"Low activity ({days_since_activity} days since last update)",
                "details": {
                    "days_since_activity": days_since_activity,
                    "total_contributions": total_contributions,
                    "target_achievement_pct": round(target_achievement_pct, 1) if target_achievement_pct else None,
                },
            }

        # YELLOW: Low consensus (< 3 contributors)
        if total_contributions < 3:
            return {
                "status": "yellow",
                "reason": f"Low consensus ({total_contributions} contribution{'s' if total_contributions != 1 else ''})",
                "details": {
                    "days_since_activity": days_since_activity,
                    "total_contributions": total_contributions,
                    "target_achievement_pct": round(target_achievement_pct, 1) if target_achievement_pct else None,
                },
            }

        # YELLOW: Approaching target date and not on track (< 7 days away)
        if target_date_status == "approaching" and target_achievement_pct and target_achievement_pct < 90:
            return {
                "status": "yellow",
                "reason": f"Target deadline approaching - {target_achievement_pct:.0f}% achieved",
                "details": {
                    "days_since_activity": days_since_activity,
                    "target_achievement_pct": round(target_achievement_pct, 1),
                    "target_status": "approaching",
                },
            }

        # YELLOW: Has target but achieving 60-89%
        if target_achievement_pct is not None and 60 <= target_achievement_pct < 90:
            return {
                "status": "yellow",
                "reason": f"{target_achievement_pct:.0f}% of target (needs improvement)",
                "details": {
                    "days_since_activity": days_since_activity,
                    "target_achievement_pct": round(target_achievement_pct, 1),
                },
            }

        # GREEN: Everything is good!
        reason_parts = ["Recent activity"]
        if target_achievement_pct is not None and target_achievement_pct >= 90:
            reason_parts.append(f"{target_achievement_pct:.0f}% of target")
        if total_contributions >= 3:
            reason_parts.append(f"{total_contributions} contributions")

        return {
            "status": "green",
            "reason": ", ".join(reason_parts),
            "details": {
                "days_since_activity": days_since_activity,
                "total_contributions": total_contributions,
                "target_achievement_pct": round(target_achievement_pct, 1) if target_achievement_pct else None,
            },
        }

    def _calculate_target_achievement(self):
        """
        Calculate overall target achievement percentage for this KPI.
        Returns average % across all configs that have targets.

        Respects target_direction:
        - maximize: Higher than target = >100% (good)
        - minimize: Lower than target = >100% (good)
        - exact: Within tolerance = 100%, outside = <100%
        """
        from app.services import ConsensusService

        achievements = []
        for config in self.value_type_configs:
            if config.target_value is not None and config.target_value != 0:
                consensus_result = ConsensusService.get_cell_value(config)
                if consensus_result and consensus_result.get("value") is not None:
                    try:
                        current_value = float(consensus_result["value"])
                        target_value = float(config.target_value)
                        target_direction = config.target_direction or "maximize"

                        if target_direction == "minimize":
                            # For minimize: being BELOW target is good
                            # If current < target, achievement > 100%
                            # If current > target, achievement < 100%
                            if current_value == 0:
                                achievement_pct = 100  # At minimum is perfect
                            else:
                                achievement_pct = (target_value / current_value) * 100

                        elif target_direction == "exact":
                            # For exact: being within tolerance is 100%
                            tolerance_pct = config.target_tolerance_pct or 10
                            tolerance = target_value * (tolerance_pct / 100)
                            diff = abs(current_value - target_value)

                            if diff <= tolerance:
                                # Within tolerance = 100%
                                achievement_pct = 100
                            else:
                                # Outside tolerance: scale down based on distance
                                # At 2x tolerance = 50%, at 3x = 33%, etc.
                                achievement_pct = max(0, 100 - ((diff - tolerance) / target_value * 100))

                        else:  # maximize (default)
                            # For maximize: being ABOVE target is good
                            achievement_pct = (current_value / target_value) * 100

                        achievements.append(achievement_pct)
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass

        if achievements:
            return sum(achievements) / len(achievements)
        return None

    def _check_target_date_status(self):
        """
        Check if any KPI configs have target dates and their status.

        Returns:
            - "overdue": Target date has passed
            - "approaching": Target date within 7 days
            - "ok": Target date > 7 days away
            - None: No target dates set
        """
        from datetime import date

        today = date.today()
        earliest_target = None

        for config in self.value_type_configs:
            if config.target_date:
                if earliest_target is None or config.target_date < earliest_target:
                    earliest_target = config.target_date

        if earliest_target is None:
            return None

        days_until_target = (earliest_target - today).days

        if days_until_target < 0:
            return "overdue"
        elif days_until_target <= 7:
            return "approaching"
        else:
            return "ok"
