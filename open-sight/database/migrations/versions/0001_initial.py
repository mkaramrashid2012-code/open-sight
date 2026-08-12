from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table("cameras", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("name", sa.String(120), nullable=False, unique=True), sa.Column("rtsp_url", sa.Text(), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_cameras_name", "cameras", ["name"], unique=False)
    op.create_table("detections", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False), sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("object_class", sa.String(64), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("track_id", sa.Integer(), nullable=True), sa.Column("bbox", postgresql.JSONB(), nullable=False), sa.Column("attributes", postgresql.JSONB(), nullable=False), sa.Column("embedding", Vector(512), nullable=True))
    for name, col in [("camera", "camera_id"),("timestamp","timestamp"),("object_class","object_class"),("track_id","track_id")]: op.create_index(f"ix_detections_{name}", "detections", [col])

def downgrade():
    op.drop_table("detections"); op.drop_table("cameras")
