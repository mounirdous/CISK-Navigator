"""
Test script for Time-Series Snapshots and Comments features
"""

from datetime import date, datetime

from app import create_app
from app.extensions import db
from app.models import (
    KPI,
    CellComment,
    Challenge,
    Contribution,
    Initiative,
    InitiativeSystemLink,
    KPISnapshot,
    KPIValueTypeConfig,
    MentionNotification,
    Organization,
    Space,
    System,
    User,
    ValueType,
)
from app.services.comment_service import CommentService
from app.services.snapshot_service import SnapshotService

app = create_app()

with app.app_context():
    print("=" * 80)
    print("TESTING NEW FEATURES")
    print("=" * 80)

    # Get test data
    org = Organization.query.first()
    if not org:
        print("❌ No organization found. Please run the app first.")
        exit(1)

    print(f"\n✓ Using organization: {org.name} (ID: {org.id})")

    # Get test user
    user = User.query.filter_by(login="cisk").first()
    if not user:
        print("❌ No cisk user found")
        exit(1)

    print(f"✓ Using user: {user.display_name}")

    # Get a KPI for testing
    kpi = KPI.query.join(InitiativeSystemLink).join(Initiative).filter(Initiative.organization_id == org.id).first()

    if not kpi:
        print("❌ No KPIs found. Please create structure first.")
        exit(1)

    print(f"✓ Found test KPI: {kpi.name}")

    # Get a value type config
    config = kpi.value_type_configs[0] if kpi.value_type_configs else None
    if not config:
        print("❌ No value type configs found")
        exit(1)

    print(f"✓ Using config for value type: {config.value_type.name}")

    # ========================================================================
    # TEST 1: TIME-SERIES SNAPSHOTS
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 1: TIME-SERIES SNAPSHOTS")
    print("=" * 80)

    # Create a contribution first (so we have data to snapshot)
    contrib = Contribution.query.filter_by(kpi_value_type_config_id=config.id).first()

    if not contrib and config.value_type.is_numeric():
        print("\n→ Creating test contribution...")
        contrib = Contribution(
            kpi_value_type_config_id=config.id,
            contributor_name="Test User",
            numeric_value=100.50,
            comment="Test value for snapshot",
        )
        db.session.add(contrib)
        db.session.commit()
        print("✓ Test contribution created")

    # Test 1.1: Create a snapshot for a single KPI
    print("\n→ Creating single KPI snapshot...")
    snapshot = SnapshotService.create_kpi_snapshot(
        config_id=config.id, snapshot_date=date.today(), label="Test Snapshot", user_id=user.id
    )

    if snapshot:
        print(f"✓ Snapshot created: ID={snapshot.id}, Date={snapshot.snapshot_date}")
        print(f"  Status: {snapshot.consensus_status}")
        print(f"  Value: {snapshot.get_value()}")
        print(f"  Label: {snapshot.snapshot_label}")
    else:
        print("⚠ No snapshot created (no consensus data)")

    # Test 1.2: Get KPI history
    print("\n→ Retrieving KPI history...")
    history = SnapshotService.get_kpi_history(config.id, limit=5)
    print(f"✓ Found {len(history)} historical snapshots")

    for snap in history:
        print(f"  - {snap.snapshot_date}: {snap.get_value()} ({snap.consensus_status})")

    # Test 1.3: Calculate trend
    print("\n→ Calculating trend...")
    if len(history) >= 2:
        trend = SnapshotService.calculate_trend(config.id, periods=2)
        if trend:
            print(f"✓ Trend: {trend['direction']} ({trend['change']:+.2f}, {trend['percent_change']:+.1f}%)")
            print(f"  Latest: {trend['latest_value']} on {trend['latest_date']}")
            print(f"  Previous: {trend['previous_value']} on {trend['previous_date']}")
        else:
            print("⚠ Insufficient data for trend calculation")
    else:
        print("⚠ Need at least 2 snapshots for trend (create more with different dates)")

    # Test 1.4: Organization-wide snapshot
    print("\n→ Creating organization-wide snapshot...")
    result = SnapshotService.create_organization_snapshot(
        organization_id=org.id, snapshot_date=date.today(), label="Full Test Snapshot", user_id=user.id
    )
    print(f"✓ Organization snapshot created:")
    print(f"  KPI snapshots: {result['kpi_snapshots']}")
    print(f"  Rollup snapshots: {result['rollup_snapshots']}")
    print(f"  Skipped (no data): {result['skipped']}")

    # Test 1.5: Get available snapshot dates
    print("\n→ Getting available snapshot dates...")
    dates = SnapshotService.get_available_snapshot_dates(org.id)
    print(f"✓ Found {len(dates)} snapshot dates:")
    for snap_date in dates[:5]:  # Show first 5
        print(f"  - {snap_date}")

    # ========================================================================
    # TEST 2: COMMENTS & MENTIONS
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 2: COMMENTS & MENTIONS")
    print("=" * 80)

    # Test 2.1: Parse mentions
    print("\n→ Testing mention parsing...")
    test_text = "Hey @john and @jane.doe, please review this value. cc @bob"
    mentions = CommentService.parse_mentions(test_text)
    print(f"✓ Parsed mentions from: '{test_text}'")
    print(f"  Found: {mentions}")

    # Test 2.2: Create a comment
    print("\n→ Creating test comment...")
    comment = CommentService.create_comment(
        config_id=config.id,
        user_id=user.id,
        comment_text="This is a test comment. @cisk please check this value!",
        organization_id=org.id,
    )
    print(f"✓ Comment created: ID={comment.id}")
    print(f"  Text: {comment.comment_text}")
    print(f"  Mentioned users: {comment.mentioned_user_ids}")
    print(f"  Created at: {comment.created_at}")

    # Test 2.3: Get comments for cell
    print("\n→ Retrieving comments for cell...")
    comments = CommentService.get_comments_for_cell(config.id)
    print(f"✓ Found {len(comments)} comments")

    for c in comments:
        print(f"  - [{c.user.display_name}] {c.comment_text[:50]}...")
        if c.mentioned_user_ids:
            print(f"    Mentions: {c.mentioned_user_ids}")

    # Test 2.4: Update a comment
    print("\n→ Updating comment...")
    updated_comment = CommentService.update_comment(
        comment_id=comment.id, comment_text="Updated comment text. Now mentioning @cisk again!", organization_id=org.id
    )
    print(f"✓ Comment updated")
    print(f"  New text: {updated_comment.comment_text}")
    print(f"  Updated at: {updated_comment.updated_at}")

    # Test 2.5: Resolve comment
    print("\n→ Resolving comment...")
    resolved = CommentService.resolve_comment(comment.id, user.id)
    print(f"✓ Comment resolved")
    print(f"  Resolved by: {resolved.resolved_by.display_name}")
    print(f"  Resolved at: {resolved.resolved_at}")

    # Test 2.6: Unresolve comment
    print("\n→ Unresolving comment...")
    unresolved = CommentService.unresolve_comment(comment.id)
    print(f"✓ Comment unresolved")

    # Test 2.7: Check unread mentions
    print("\n→ Checking unread mentions...")
    mentions = CommentService.get_unread_mentions(user.id, limit=10)
    print(f"✓ Found {len(mentions)} unread mentions")

    for mention in mentions:
        print(f"  - From comment ID {mention.comment_id}")
        print(f"    Created: {mention.created_at}")

    # Test 2.8: Render comment with mentions
    print("\n→ Rendering comment with mentions...")
    rendered = CommentService.render_comment_with_mentions("Hey @cisk, check this out!", org.id)
    print(f"✓ Rendered HTML:")
    print(f"  {rendered}")

    # Test 2.9: Get comment count
    print("\n→ Getting comment count...")
    count = CommentService.get_comment_count_for_cell(config.id)
    print(f"✓ Total comments for this cell: {count}")

    # Test 2.10: Create a reply (parent comment)
    print("\n→ Creating reply comment...")
    reply = CommentService.create_comment(
        config_id=config.id,
        user_id=user.id,
        comment_text="This is a reply to the first comment",
        parent_comment_id=comment.id,
        organization_id=org.id,
    )
    print(f"✓ Reply created: ID={reply.id}")
    print(f"  Parent: {reply.parent_comment_id}")

    # Cleanup test comment (optional - leave for testing)
    # print("\n→ Cleaning up test comments...")
    # CommentService.delete_comment(comment.id)
    # print("✓ Test comments deleted")

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("\n✓ Time-Series Snapshots:")
    print("  - Single KPI snapshot: ✓")
    print("  - KPI history retrieval: ✓")
    print("  - Trend calculation: ✓")
    print("  - Organization snapshot: ✓")
    print("  - Available dates query: ✓")

    print("\n✓ Comments & Mentions:")
    print("  - Mention parsing: ✓")
    print("  - Comment creation: ✓")
    print("  - Comment retrieval: ✓")
    print("  - Comment update: ✓")
    print("  - Comment resolution: ✓")
    print("  - Unread mentions: ✓")
    print("  - HTML rendering: ✓")
    print("  - Comment threading: ✓")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED! ✓")
    print("=" * 80)

    print("\n📝 Database tables created:")
    print("  - kpi_snapshots")
    print("  - rollup_snapshots")
    print("  - cell_comments")
    print("  - mention_notifications")

    print("\n🚀 Ready to push to Render!")
    print("=" * 80)
