"""SQLAlchemy model for ad creative variations."""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import database


class Variation(database.Base):
    __tablename__ = "variations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ad_id = Column(Integer, ForeignKey("ads.id"), index=True)

    # Variation content
    creative_text = Column(Text)
    landing_url = Column(String(2000))
    thumbnail_url = Column(String(1000))

    # Targeting hints
    platform_target = Column(String(50), default="all")  # facebook/instagram/messenger/audience_network/all
    device_target = Column(String(20), default="all")  # desktop/mobile/all
    geo_target = Column(String(200))  # "US,UK,CA" or null

    # Classification
    is_decoy = Column(Boolean, default=False)
    is_real = Column(Boolean, default=False)
    variation_index = Column(Integer, default=0)  # which variation number

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ad = relationship("Ad", back_populates="variations")
    landers = relationship("Lander", back_populates="variation")

    def __repr__(self) -> str:
        return f"<Variation {self.id} | ad={self.ad_id} | real={self.is_real}>"
