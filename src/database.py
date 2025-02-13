# src/database.py
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime
from databases import Database
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./system_health.db")
database = Database(DATABASE_URL)
metadata = MetaData()

metadata_table = Table(
    "metadata",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(50)),
    Column("environment", String(50)),
    Column("location", String(100)),
)
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String, unique=True),
    Column("username", String),
    Column("password_hash", String),
    Column("api_key", String, unique=True),
    Column("created_at", DateTime)
)

alerts_table = Table(
    "alerts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("timestamp", DateTime, default=datetime.utcnow),
    Column("metric_type", String(50)),
    Column("threshold", Float),
    Column("current_value", Float),
    Column("status", String(20))
)

metrics_history_table = Table(
    "metrics_history",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("timestamp", DateTime, default=datetime.utcnow),
    Column("cpu_percent", Float),
    Column("memory_percent", Float),
    Column("disk_percent", Float)
)