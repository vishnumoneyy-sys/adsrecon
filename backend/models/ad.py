"""SQLAlchemy model for Meta Ads Library ads."""
from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import database


class Ad(database.Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Meta Ads Library data
    library_id = Column(String(50), unique=True, index=True)  # Meta's internal ID
    page_id = Column(String(50), index=True)  # Facebook page ID
    page_name = Column(String(500))

    # Ad content
    ad_text = Column(Text)
    primary_image_url = Column(String(1000))
    video_urls = Column(JSON, default=list)  # ["url1", "url2"]

    # Landing page
    landing_url_clean = Column(String(2000))  # URL as shown in Meta (before cloaking)
    landing_url_actual = Column(String(2000))  # URL after cloaking bypass

    # Status and metadata
    status = Column(String(20), default="active")  # active/inactive
    platforms = Column(JSON, default=list)  # ["facebook", "instagram", "messenger", "audience_network"]
    days_running = Column(Integer, default=0)
    impressions_estimate = Column(String(50))  # "952" or "1.2K"
    spend_estimate = Column(String(50))        # "$100-$500" from Graph API
    countries = Column(JSON, default=list)      # ["US","GB"] delivery countries

    # Classification
    category = Column(String(50))  # nutra vertical
    is_real_nutra = Column(Boolean, default=False)
    nutra_score = Column(Integer, default=0)  # 0-100 aggression score

    # Cloaking
    cloak_status = Column(String(20), default="pending")  # pending/passed/failed/cloaked
    cloak_service_guess = Column(String(100))  # "keitaro", "bemob", "custom"
    fbclid = Column(String(500))  # The fbclid extracted from Meta's redirect

    # User data
    saved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    variations = relationship("Variation", back_populates="ad", cascade="all, delete-orphan")
    landers = relationship("Lander", back_populates="ad", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Ad {self.library_id} | {self.page_name} | {self.status}>"
