"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── categories ─────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
    )

    # ── users ──────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="volunteer"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )

    # ── user_settings ──────────────────────────────────────
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "search_radius_km", sa.Integer(), nullable=False, server_default="10"
        ),
        sa.Column(
            "show_only_subscriptions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("language", sa.String(10), nullable=False, server_default="ru"),
        sa.Column("theme", sa.String(10), nullable=False, server_default="light"),
        sa.Column("main_organization_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── user_locations ─────────────────────────────────────
    op.create_table(
        "user_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── refresh_tokens ─────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )

    # ── organizer_applications ─────────────────────────────
    op.create_table(
        "organizer_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "uq_organizer_applications_pending",
        "organizer_applications",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )

    # ── organizations ──────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True
        ),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )

    # ── organization_organizers ────────────────────────────
    op.create_table(
        "organization_organizers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column(
            "role_in_org", sa.String(20), nullable=False, server_default="organizer"
        ),
        sa.Column("added_by", sa.Integer(), nullable=True),
        sa.Column(
            "added_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )
    op.create_index(
        "uq_organization_organizers_active",
        "organization_organizers",
        ["organization_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index(
        "uq_organization_organizers_one_owner",
        "organization_organizers",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("role_in_org = 'owner' AND is_active = true"),
    )

    # ── events ─────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("max_participants", sa.Integer(), server_default="100"),
        sa.Column("qr_secret", sa.String(64), nullable=True),
        sa.Column(
            "qr_check_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("image_url", sa.String(512), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column(
            "has_custom_roles",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # ── event_roles ────────────────────────────────────────
    op.create_table(
        "event_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("events.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hours_value", sa.Float(), nullable=False, server_default="4.0"),
        sa.Column("max_participants", sa.Integer(), nullable=True),
    )

    # ── participations ─────────────────────────────────────
    op.create_table(
        "participations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "role_id", sa.Integer(), sa.ForeignKey("event_roles.id"), nullable=True
        ),
        sa.Column("status", sa.String(20), server_default="registered"),
        sa.Column("registered_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("checked_in_at", sa.DateTime(), nullable=True),
    )

    # ── subscriptions ──────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="volunteer"),
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── subscription_logs ──────────────────────────────────
    op.create_table(
        "subscription_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    # ── chats ──────────────────────────────────────────────
    op.create_table(
        "chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("scheduled_delete_at", sa.DateTime(), nullable=True),
        sa.Column("deletion_config", sa.JSON(), nullable=True),
    )

    # ── chat_members ───────────────────────────────────────
    op.create_table(
        "chat_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column(
            "joined_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("left_at", sa.DateTime(), nullable=True),
        sa.Column(
            "is_muted", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )

    # ── messages ───────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id"), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("attachment_url", sa.String(512), nullable=True),
        sa.Column(
            "is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── volunteer_stats ────────────────────────────────────
    op.create_table(
        "volunteer_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("organization_id", sa.Integer(), nullable=True, index=True),
        sa.Column("organization_name_snapshot", sa.String(255), nullable=True),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("hours_worked", sa.Float(), server_default="0.0"),
        sa.Column("events_completed", sa.Integer(), server_default="0"),
        sa.Column("last_activity", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── monthly_stats ──────────────────────────────────────
    op.create_table(
        "monthly_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("hours_worked", sa.Float(), server_default="0.0"),
        sa.Column("events_completed", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )

    # ── preferred_roles ────────────────────────────────────
    op.create_table(
        "preferred_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("score", sa.Float(), server_default="0.0"),
        sa.Column("events_count", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )

    # ── notification_tokens ────────────────────────────────
    op.create_table(
        "notification_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column(
            "device_token", sa.String(255), nullable=False, unique=True, index=True
        ),
        sa.Column("platform", sa.String(20), server_default="ANDROID"),
        sa.Column("app_version", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── notifications ──────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), server_default="NORMAL"),
        sa.Column("data", sa.JSON(), server_default="{}"),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── push_logs ──────────────────────────────────────────
    op.create_table(
        "push_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "notification_id",
            sa.Integer(),
            sa.ForeignKey("notifications.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("device_token", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ── feed_service_logs ──────────────────────────────────
    op.create_table(
        "feed_service_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), index=True),
        sa.Column("request_id", sa.String(100), index=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("event_count", sa.Integer(), server_default="0"),
        sa.Column("cache_hit", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            index=True,
        ),
    )

    # ── feed_event_cache ───────────────────────────────────
    op.create_table(
        "feed_event_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), index=True),
        sa.Column("event_id", sa.Integer(), index=True),
        sa.Column("cached_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("feed_event_cache")
    op.drop_table("feed_service_logs")
    op.drop_table("push_logs")
    op.drop_table("notifications")
    op.drop_table("notification_tokens")
    op.drop_table("preferred_roles")
    op.drop_table("monthly_stats")
    op.drop_table("volunteer_stats")
    op.drop_table("messages")
    op.drop_table("chat_members")
    op.drop_table("chats")
    op.drop_table("subscription_logs")
    op.drop_table("subscriptions")
    op.drop_table("participations")
    op.drop_table("event_roles")
    op.drop_table("events")
    op.drop_index("uq_organization_organizers_one_owner", "organization_organizers")
    op.drop_index("uq_organization_organizers_active", "organization_organizers")
    op.drop_table("organization_organizers")
    op.drop_table("organizations")
    op.drop_index("uq_organizer_applications_pending", "organizer_applications")
    op.drop_table("organizer_applications")
    op.drop_table("refresh_tokens")
    op.drop_table("user_locations")
    op.drop_table("user_settings")
    op.drop_table("users")
    op.drop_table("categories")
