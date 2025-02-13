# System Health Monitoring & Alerting Tool

A local system health monitoring tool built with FastAPI that collects real-time metrics, manages metadata, and provides alerting capabilities for system health monitoring.

## Features

### Core Functionality
- Real-time system metrics monitoring (CPU, Memory, Disk)
- Metadata management through API endpoints
- Configurable alert thresholds
- Historical metrics tracking
- Slack notifications for alerts

### API Endpoints

#### System Metrics
- `GET /api/metrics` - Get current system metrics
- `GET /api/metrics/history` - Get historical metrics data

#### Metadata Management
- `POST /api/metadata` - Create/Update system metadata
- `GET /api/metadata` - Retrieve all metadata
- `DELETE /api/metadata/{name}` - Delete specific metadata

#### Alerts
- `GET /api/alerts` - Get all alerts
- `PUT /api/alerts/{alert_id}/resolve` - Resolve specific alert
- `POST /api/test-notification` - Test Slack notification system

## Technical Stack

- **Backend Framework**: FastAPI
- **Database**: SQLite
- **System Metrics**: psutil
- **Authentication**: API Key-based
- **Notifications**: Slack Webhooks

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd system-health-monitor
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file with configuration:
```env
DATABASE_URL=sqlite:///./monitoring.db
API_KEY=your-api-key-here
CPU_THRESHOLD=80
MEMORY_THRESHOLD=85
DISK_THRESHOLD=90
SLACK_WEBHOOK_URL=your-slack-webhook-url
```

## Running the Application

1. Start the FastAPI server:
```bash
uvicorn main:app --reload
```

2. Access the API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing the Application

The project includes a test script (`test_api.py`) to verify all API endpoints and functionality.

### Running the Test Script

1. Make sure the FastAPI server is running

2. Run the test script:
```bash
python test_api.py
```

The test script will:
- Test all API endpoints
- Verify authentication
- Check system metrics collection
- Test metadata operations
- Verify alert functionality
- Test notification system
- Optionally monitor the system for 5 minutes

### Example Test Code
```python
import requests

# Configuration
headers = {"X-API-Key": "your-api-key"}

# Test current metrics
response = requests.get("http://localhost:8000/api/metrics", headers=headers)
print(response.json())

# Test notification system
response = requests.post("http://localhost:8000/api/test-notification", headers=headers)
print(response.json())
```

## Project Structure
```
system-health-monitor/src
├── main.py           # Main application file
├── database.py       # Database configuration
├── test_api.py       # API testing script

system-health-monitor
├── requirements.txt
└── .env
```

## Design Choices

### Database Selection
- SQLite was chosen for its simplicity and zero-configuration setup
- Tables designed for efficient querying of historical data

### Alert Logic
- Configurable thresholds via environment variables
- Background task checks metrics every minute
- Alerts stored with timestamps for historical tracking
- Resolution system with Slack notifications

### Security
- API Key authentication for all endpoints
- Input validation using Pydantic models
- Secure error handling to prevent information leakage

## Deployment

The application is deployed on Railway platform. Live API endpoint: [Your-Railway-URL]

## Tools Used

In the development of this project, the following AI tools were utilized:
- Chatgpt(LLM): For assistance with development 


