"""SQLAlchemy model for tracked Meta ad campaigns."""
from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
import database


class Campaign(database.Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500))
    description = Column(String(2000), nullable=True)

    # Tracking
    page_ids = Column(JSON, default=list)  # ["page_id_1", "page_id_2"]
    ad_ids = Column(JSON, default=list)  # [1, 2, 3]

    # Filters applied
    category_filter = Column(String(50), nullable=True)
    geo_filter = Column(String(50), nullable=True)
    status_filter = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Campaign {self.id} | {self.name} | {len(self.ad_ids or [])} ads>"
