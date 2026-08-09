from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from app.database.connection import Base


class DiscoveryFindingAssetLink(Base):
    """One-to-one record of an explicit user conversion from a finding to an asset."""

    __tablename__ = "discovery_finding_asset_links"

    finding_id = Column(
        String,
        ForeignKey("evidence_findings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_id = Column(
        String,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_context = Column(String, nullable=False, default="manual_conversion", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
