from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Enum, DateTime, ForeignKey,
    DECIMAL, JSON, Boolean, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("admin", "operator", "viewer"), default="operator")
    avatar = Column(String(255), default=None)
    created_at = Column(DateTime, server_default=func.now())

    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), default="新对话")
    is_deleted = Column(Boolean, default=False, server_default="0")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at", passive_deletes=True)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum("user", "assistant", "system"), nullable=False)
    content = Column(Text)
    msg_type = Column(Enum("text", "voice", "docx"), default="text")
    file_url = Column(String(500), default=None)
    created_at = Column(DateTime, server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class PumpStation(Base):
    __tablename__ = "pump_stations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    location = Column(String(200))
    meta_json = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

    units = relationship("PumpUnit", back_populates="station")


class PumpUnit(Base):
    __tablename__ = "pump_units"
    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(Integer, ForeignKey("pump_stations.id", ondelete="CASCADE"), nullable=False)
    unit_name = Column(String(50))
    rated_power_kw = Column(DECIMAL(10, 2))
    rated_flow = Column(DECIMAL(10, 2))
    meta_json = Column(JSON)

    station = relationship("PumpStation", back_populates="units")


class OperatingPoint(Base):
    __tablename__ = "operating_points"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    station_id = Column(Integer, ForeignKey("pump_stations.id", ondelete="CASCADE"), nullable=False)
    flow = Column(DECIMAL(10, 2))
    head = Column(DECIMAL(10, 2))
    power = Column(DECIMAL(10, 2))
    voltage = Column(DECIMAL(10, 2))
    current_amp = Column(DECIMAL(10, 2))
    energy_wh = Column(DECIMAL(12, 2))
    ts = Column(DateTime, nullable=False)


class ScheduleTask(Base):
    __tablename__ = "schedule_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(Integer, nullable=True)
    objective_text = Column(Text)
    constraints_json = Column(JSON)
    status = Column(
        Enum("created", "parsing", "optimizing", "validating", "done", "failed"),
        default="created",
    )
    created_at = Column(DateTime, server_default=func.now())

    plans = relationship("SchedulePlan", back_populates="task")


class SchedulePlan(Base):
    __tablename__ = "schedule_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("schedule_tasks.id", ondelete="CASCADE"), nullable=False)
    plan_json = Column(JSON)
    energy_kwh = Column(DECIMAL(10, 2))
    explanation = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    task = relationship("ScheduleTask", back_populates="plans")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String(100))
    payload_json = Column(JSON)
    ts = Column(DateTime, server_default=func.now())
