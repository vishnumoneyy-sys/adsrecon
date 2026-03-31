"""SQLAlchemy model for ripped landing pages."""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import database


class Lander(database.Base):
    __tablename__ = "landers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ad_id = Column(Integer, ForeignKey("ads.id"), index=True)
    variation_id = Column(Integer, ForeignKey("variations.id"), nullable=True)

    # Storage paths
    screenshot_path = Column(String(500))
    html_dump_path = Column(String(500))

    # Content extracted
    video_urls = Column(JSON, default=list)
    phone_numbers = Column(JSON, default=list)
    email_addresses = Column(JSON, default=list)

    # Detection results
    cloak_detected = Column(Boolean, default=False)
    cloak_service_guess = Column(String(100))
    geo_signals = Column(JSON, default=dict)  # {"detected_country": "US", "cloaking_signals": [...]}

    # Device used to rip
    device_used = Column(String(20), default="desktop")  # desktop/mobile
    proxy_used = Column(String(500), nullable=True)

    # Final URL after all redirects
    final_url = Column(String(2000))

    # Page title
    title = Column(String(500))

    # Access info
    accessed_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(String(500), nullable=True)

    # Relationships
    ad = relationship("Ad", back_populates="landers")
    variation = relationship("Variation", back_populates="landers")

    def __repr__(self) -> str:
        return f"<Lander {self.id} | ad={self.ad_id} | cloak={self.cloak_detected}>"
