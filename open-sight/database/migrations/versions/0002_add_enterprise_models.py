from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision = "0002_add_enterprise_models"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # Create enums
    op.execute("CREATE TYPE trackstate AS ENUM ('new', 'tentative', 'active', 'lost', 'recovered', 'ended')")
    op.execute("CREATE TYPE eventtype AS ENUM ('person_detected', 'vehicle_detected', 'intrusion', 'loitering', 'line_crossing', 'crowd', 'object_abandoned', 'wrong_direction', 'camera_offline', 'camera_reonline')")
    op.execute("CREATE TYPE role_enum AS ENUM ('admin', 'security_manager', 'operator', 'investigator', 'auditor', 'viewer')")
    op.execute("CREATE TYPE permission_enum AS ENUM ('camera.read', 'camera.manage', 'event.read', 'event.export', 'evidence.read', 'evidence.export', 'user.manage', 'audit.read', 'system.manage')")
    
    # Add columns to cameras table
    op.add_column('cameras', sa.Column('status', sa.String(32), nullable=False, server_default='offline'))
    op.add_column('cameras', sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True))
    op.add_column('cameras', sa.Column('fps_current', sa.Float(), nullable=True))
    op.add_column('cameras', sa.Column('frames_dropped', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('cameras', sa.Column('reconnect_count', sa.Integer(), nullable=False, server_default='0'))
    op.create_index('ix_cameras_status', 'cameras', ['status'])
    
    # Modify detections table - add track_id index if not exists
    op.create_index('ix_detections_track_id', 'detections', ['track_id'], unique=False, if_not_exists=True)
    
    # Create tracks table
    op.create_table('tracks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('track_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('camera_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('state', sa.Enum('new', 'tentative', 'active', 'lost', 'recovered', 'ended', name='trackstate'), nullable=False, server_default='new'),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('detection_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('confidence_avg', sa.Float(), nullable=True),
        sa.Column('confidence_max', sa.Float(), nullable=True),
        sa.Column('current_bbox', postgresql.JSONB(), nullable=True),
        sa.Column('trajectory', postgresql.JSONB(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('appearance_embedding', Vector(512), nullable=True),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tracks_track_uuid', 'tracks', ['track_uuid'], unique=True)
    op.create_index('ix_tracks_camera_id', 'tracks', ['camera_id'])
    op.create_index('ix_tracks_track_id', 'tracks', ['track_id'])
    op.create_index('ix_tracks_state', 'tracks', ['state'])
    op.create_index('ix_tracks_first_seen', 'tracks', ['first_seen'])
    op.create_index('ix_tracks_camera_firstseen', 'tracks', ['camera_id', 'first_seen'])
    op.create_index('ix_tracks_state_lastseen', 'tracks', ['state', 'last_seen'])
    
    # Create events table
    op.create_table('events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('camera_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.Enum(name='eventtype'), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('thumbnail_path', sa.Text(), nullable=True),
        sa.Column('clip_path', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_start_time', 'events', ['start_time'])
    op.create_index('ix_events_track_id', 'events', ['track_id'])
    op.create_index('ix_events_type_starttime', 'events', ['event_type', 'start_time'])
    op.create_index('ix_events_camera_createtime', 'events', ['camera_id', 'created_at'])
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(120), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    
    # Create user_roles table
    op.create_table('user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('admin', 'security_manager', 'operator', 'investigator', 'auditor', 'viewer', name='role_enum'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role')
    )
    
    # Create permissions enum and role_permissions table
    op.create_table('role_permissions',
        sa.Column('role', sa.Enum('admin', 'security_manager', 'operator', 'investigator', 'auditor', 'viewer', name='role_enum'), nullable=False),
        sa.Column('permission', sa.Enum('camera.read', 'camera.manage', 'event.read', 'event.export', 'evidence.read', 'evidence.export', 'user.manage', 'audit.read', 'system.manage', name='permission_enum'), nullable=False),
        sa.PrimaryKeyConstraint('role', 'permission')
    )
    
    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('permissions', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)
    
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('resource', sa.String(64), nullable=False),
        sa.Column('resource_id', sa.String(120), nullable=True),
        sa.Column('result', sa.String(32), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_username', 'audit_logs', ['username'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_timestamp_action', 'audit_logs', ['timestamp', 'action'])
    
    # Create evidence_holds table
    op.create_table('evidence_holds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('event_ids', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_holds_is_active', 'evidence_holds', ['is_active', 'expires_at'])


def downgrade():
    op.drop_table('evidence_holds')
    op.drop_table('audit_logs')
    op.drop_table('api_keys')
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('events')
    op.drop_table('tracks')
    
    # Remove added columns from cameras
    op.drop_index('ix_cameras_status', table_name='cameras')
    op.drop_column('cameras', 'reconnect_count')
    op.drop_column('cameras', 'frames_dropped')
    op.drop_column('cameras', 'fps_current')
    op.drop_column('cameras', 'last_seen')
    op.drop_column('cameras', 'status')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS permission_enum")
    op.execute("DROP TYPE IF EXISTS role_enum")
    op.execute("DROP TYPE IF EXISTS eventtype")
    op.execute("DROP TYPE IF EXISTS trackstate")
