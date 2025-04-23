from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from db import Base

class ServiceConfig(Base):
    __tablename__ = "service_configs"
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, unique=True, nullable=False)
    config_json = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    job_code = Column(String, unique=True, nullable=True)
    description = Column(Text)
    cron_expr = Column(String, nullable=True)
    interval_minutes = Column(Integer, nullable=False, default=0)
    next_run_time = Column(DateTime)
    last_run_time = Column(DateTime)
    is_active = Column(Boolean, nullable=False, default=True)

class VoiceSession(Base):
    __tablename__ = "voice_sessions"
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    session_status = Column(String, default="ACTIVE")
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime)

class VoicePrompt(Base):
    __tablename__ = "voice_prompts"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("voice_sessions.id", ondelete="CASCADE"), nullable=False)
    prompt_text = Column(Text, nullable=False)
    played_at = Column(DateTime, server_default=func.now())

class VoiceResponse(Base):
    __tablename__ = "voice_responses"
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("voice_prompts.id", ondelete="CASCADE"), nullable=False)
    recognized_text = Column(Text)
    mapped_option = Column(String)
    responded_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="CONFIRMED")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    channel_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="SUCCESS")

class TeamsPost(Base):
    __tablename__ = "teams_posts"
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    channel_name = Column(String, nullable=False)
    message_id = Column(String)
    parent_message_id = Column(String)
    content = Column(Text, nullable=False)
    posted_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="SUCCESS")

class TPEntry(Base):
    __tablename__ = "tp_entries"
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(Text, nullable=False)
    sheet_name = Column(String, nullable=False)
    values_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="SUCCESS")

class ArtifactUpload(Base):
    __tablename__ = "artifact_uploads"
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(Text, nullable=False)
    file_name = Column(String, nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="SUCCESS")

class FormSubmission(Base):
    __tablename__ = "form_submissions"
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    form_id = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    submitted_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="SUCCESS")