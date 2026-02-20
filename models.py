from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String(100))
    surname = Column(String(100))
    age = Column(Integer)
    role = Column(String(50))
    photo_file_id = Column(String(255))
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    is_subscribed = Column(Boolean, default=False)
    last_active = Column(DateTime, default=func.now())
    registered_at = Column(DateTime, default=func.now())
    
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")

class Sponsor(Base):
    __tablename__ = "sponsors"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    url = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)

class Broadcast(Base):
    __tablename__ = "broadcasts"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(Text)
    content_type = Column(String(20))
    content = Column(JSON)
    button_text = Column(String(50))
    button_url = Column(String(255))
    sent_at = Column(DateTime, default=func.now())

class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subcategory_id = Column(Integer, nullable=False)  # ID из JSON
    current_material_index = Column(Integer, default=0)
    completed_materials = Column(JSON, default=list)
    last_accessed = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="progress")

class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(10), default="🏆")
    
    user_achievements = relationship("UserAchievement", back_populates="achievement", cascade="all, delete-orphan")

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

class Bookmark(Base):
    __tablename__ = "bookmarks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    material_id = Column(Integer, nullable=False)  
    subcategory_id = Column(Integer, nullable=False)  
    material_name = Column(String(200))
    added_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="bookmarks")