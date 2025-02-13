from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import psutil
import asyncio
import requests
from .database import database, metadata_table, alerts_table, metrics_history_table,users_table
from sqlalchemy import create_engine, select, and_,Table, Column, Integer, String, DateTime
from pydantic import BaseModel, validator,EmailStr
import os
from dotenv import load_dotenv
import uuid
from passlib.context import CryptContext

load_dotenv()

# Models for request validation
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    api_key: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str
class MetadataUpdate(BaseModel):
    """
    Model for metadata updates with validation
    """
    name: str
    environment: str
    location: str

    @validator('name', 'environment', 'location')
    def validate_string_length(cls, v):
        if len(v) < 1 or len(v) > 50:
            raise ValueError('String length must be between 1 and 50 characters')
        return v

class AlertResponse(BaseModel):
    """
    Model for alert responses
    """
    id: int
    timestamp: datetime
    metric_type: str
    threshold: float
    current_value: float
    status: str

# Initialize FastAPI app
app = FastAPI(
    title="System Health Monitor",
    description="A tool for monitoring system health metrics and sending alerts",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_api_key() -> str:
    return str(uuid.uuid4())

# Configuration

CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "80"))
MEMORY_THRESHOLD = float(os.getenv("MEMORY_THRESHOLD", "85"))
DISK_THRESHOLD = float(os.getenv("DISK_THRESHOLD", "90"))
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# Authentication
api_key_header = APIKeyHeader(name="X-API-Key")

# verify_api_key function
async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify the API key against registered users"""
    query = users_table.select().where(users_table.c.api_key == api_key)
    user = await database.fetch_one(query)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return api_key

# Startup and shutdown events
@app.on_event("startup")
async def startup():
    """
    Initialize database and start background monitoring on startup
    """
    engine = create_engine(str(database.url))
    metadata_table.create(engine, checkfirst=True)
    alerts_table.create(engine, checkfirst=True)
    metrics_history_table.create(engine, checkfirst=True)
    await database.connect()
    asyncio.create_task(check_system_health())

@app.on_event("shutdown")
async def shutdown():
    """
    Disconnect from database on shutdown
    """
    await database.disconnect()

# Notification function
async def send_slack_alert(alert_data: dict):
    """
    Send alert to Slack channel using webhook
    """
    if not SLACK_WEBHOOK_URL:
        print("Slack webhook URL not configured")
        return
    
    try:
        # Create a formatted Slack message
        color = "#ff0000" if alert_data['status'] == "active" else "#36a64f"
        
        message = {
            "attachments": [
                {
                    "color": color,
                    "title": f"System Alert: {alert_data['metric_type']} Usage High",
                    "fields": [
                        {
                            "title": "Metric",
                            "value": alert_data['metric_type'],
                            "short": True
                        },
                        {
                            "title": "Current Value",
                            "value": f"{alert_data['current_value']}%",
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": f"{alert_data['threshold']}%",
                            "short": True
                        },
                        {
                            "title": "Status",
                            "value": alert_data['status'],
                            "short": True
                        }
                    ],
                    "footer": "System Health Monitor",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        # Send to Slack with retry logic
        for attempt in range(3):  # Try 3 times
            try:
                response = requests.post(
                    SLACK_WEBHOOK_URL,
                    json=message,
                    timeout=5
                )
                response.raise_for_status()
                print(f"Slack alert sent successfully for {alert_data['metric_type']}")
                break
            except Exception as e:
                if attempt == 2:  # Last attempt
                    raise e
                await asyncio.sleep(1)  # Wait before retry
        
    except Exception as e:
        print(f"Error sending Slack alert: {str(e)}")

# Utility functions
async def get_system_metrics():
    """
    Collect current system metrics
    """
    try:
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "cores": psutil.cpu_count()
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "percent": psutil.disk_usage('/').percent
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error collecting system metrics: {str(e)}")

async def create_alert(metric_type: str, threshold: float, current_value: float):
    """
    Create and store a new alert, send Slack notification
    """
    try:
        query = alerts_table.insert().values(
            timestamp=datetime.now(),
            metric_type=metric_type,
            threshold=threshold,
            current_value=current_value,
            status="active"
        )
        alert_id = await database.execute(query)
        
        alert_data = {
            "id": alert_id,
            "metric_type": metric_type,
            "threshold": threshold,
            "current_value": current_value,
            "status": "active",
            "timestamp": datetime.now().isoformat()
        }
        
        # Send Slack notification
        await send_slack_alert(alert_data)
        
        print(f"ALERT: {metric_type} usage at {current_value}% (threshold: {threshold}%)")
        
    except Exception as e:
        print(f"Error creating alert: {str(e)}")

async def store_historical_metrics(metrics: Dict):
    """
    Store metrics in the database for historical tracking
    """
    try:
        query = metrics_history_table.insert().values(
            timestamp=datetime.now(),
            cpu_percent=metrics["cpu"]["percent"],
            memory_percent=metrics["memory"]["percent"],
            disk_percent=metrics["disk"]["percent"]
        )
        await database.execute(query)
    except Exception as e:
        print(f"Error storing historical metrics: {str(e)}")

# Background monitoring task
async def check_system_health():
    """
    Continuous background task to monitor system health
    """
    while True:
        try:
            metrics = await get_system_metrics()
            
            # Check CPU
            if metrics["cpu"]["percent"] > CPU_THRESHOLD:
                await create_alert("CPU", CPU_THRESHOLD, metrics["cpu"]["percent"])
            
            # Check Memory
            if metrics["memory"]["percent"] > MEMORY_THRESHOLD:
                await create_alert("Memory", MEMORY_THRESHOLD, metrics["memory"]["percent"])
            
            # Check Disk
            if metrics["disk"]["percent"] > DISK_THRESHOLD:
                await create_alert("Disk", DISK_THRESHOLD, metrics["disk"]["percent"])
            
            # Store historical metrics
            await store_historical_metrics(metrics)
            
        except Exception as e:
            print(f"Error in health check: {str(e)}")
        
        await asyncio.sleep(60)  # Check every minute

# API Endpoints
@app.get("/")
async def root():
    """
    Root endpoint for basic health check
    """
    return {
        "message": "System Health Monitoring Tool",
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/api/metrics")
async def get_metrics(api_key: str = Depends(verify_api_key)):
    """
    Get current system metrics
    """
    try:
        return await get_system_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics/history")
async def get_metrics_history(
    minutes: int = 60,
    api_key: str = Depends(verify_api_key)
):
    """
    Get historical metrics for the specified time period
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        query = metrics_history_table.select().where(
            metrics_history_table.c.timestamp > cutoff_time
        ).order_by(metrics_history_table.c.timestamp.desc())
        
        results = await database.fetch_all(query)
        
        formatted_results = []
        for record in results:
            formatted_results.append({
                "timestamp": record.timestamp.isoformat(),
                "cpu_percent": round(record.cpu_percent, 2),
                "memory_percent": round(record.memory_percent, 2),
                "disk_percent": round(record.disk_percent, 2)
            })
        
        return formatted_results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving historical metrics: {str(e)}"
        )

@app.post("/api/metadata")
async def update_metadata(
    metadata: MetadataUpdate,
    api_key: str = Depends(verify_api_key)
):
    """
    Create or update system metadata
    """
    try:
        # Check if record exists
        select_query = metadata_table.select().where(
            metadata_table.c.name == metadata.name
        )
        existing = await database.fetch_one(select_query)
        
        if existing:
            # Update existing record
            query = metadata_table.update().where(
                metadata_table.c.name == metadata.name
            ).values(**metadata.dict())
            await database.execute(query)
            return {"message": "Metadata updated successfully"}
        else:
            # Insert new record
            query = metadata_table.insert().values(**metadata.dict())
            await database.execute(query)
            return {"message": "Metadata created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating metadata: {str(e)}")

@app.get("/api/metadata")
async def get_metadata(api_key: str = Depends(verify_api_key)):
    """
    Get all system metadata
    """
    try:
        query = metadata_table.select()
        return await database.fetch_all(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/metadata/{name}")
async def delete_metadata(
    name: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Delete system metadata by name
    """
    try:
        query = metadata_table.delete().where(metadata_table.c.name == name)
        result = await database.execute(query)
        if result:
            return {"message": f"Metadata for {name} deleted successfully"}
        raise HTTPException(status_code=404, detail="Metadata not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting metadata: {str(e)}")

@app.get("/api/alerts")
async def get_alerts(
    status: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """
    Get all alerts, optionally filtered by status
    """
    try:
        query = alerts_table.select()
        if status:
            query = query.where(alerts_table.c.status == status)
        return await database.fetch_all(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    api_key: str = Depends(verify_api_key)
):
    """
    Mark an alert as resolved
    """
    try:
        query = alerts_table.update().where(
            alerts_table.c.id == alert_id
        ).values(status="resolved")
        result = await database.execute(query)
        if result:
            # Send resolution notification to Slack
            alert = await database.fetch_one(
                alerts_table.select().where(alerts_table.c.id == alert_id)
            )
            if alert:
                alert_dict = dict(alert)
                alert_dict['status'] = 'resolved'
                await send_slack_alert(alert_dict)
            return {"message": f"Alert {alert_id} resolved"}
        raise HTTPException(status_code=404, detail="Alert not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test-notification")
async def test_notification(api_key: str = Depends(verify_api_key)):
    """
    Test Slack notification
    """
    test_alert = {
        "id": 0,
        "metric_type": "TEST",
        "threshold": 80.0,
        "current_value": 85.0,
        "status": "active",
        "timestamp": datetime.now().isoformat()
    }
    await send_slack_alert(test_alert)
    return {"message": "Test notification sent"}


@app.post("/api/register", response_model=User)
async def register_user(user: UserCreate):
    """Register a new user and return their API key"""
    # Check if user already exists
    query = users_table.select().where(users_table.c.email == user.email)
    existing_user = await database.fetch_one(query)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user with hashed password and API key
    api_key = generate_api_key()
    query = users_table.insert().values(
        email=user.email,
        username=user.username,
        password_hash=get_password_hash(user.password),
        api_key=api_key,
        created_at=datetime.utcnow()
    )
    user_id = await database.execute(query)
    
    return {
        "id": user_id,
        "email": user.email,
        "username": user.username,
        "api_key": api_key,
        "created_at": datetime.utcnow()
    }

@app.post("/api/login")
async def login_user(user: UserLogin):
    """Login user and return their API key"""
    query = users_table.select().where(users_table.c.email == user.email)
    db_user = await database.fetch_one(query)
    
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"api_key": db_user.api_key}

