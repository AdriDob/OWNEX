# OWNEX API Reference

Complete API reference for OWNEX Autonomous Personal Operating System.

## Base URL

```
Development: http://127.0.0.1:8000
Production: https://api.ownex.ai
```

## Authentication

Most endpoints require authentication via API key or session token.

```bash
# Set API key
export OWNEX_API_KEY="your-api-key"

# Include in requests
curl -H "Authorization: Bearer $OWNEX_API_KEY" http://127.0.0.1:8000/api/health
```

## Health & Status

### GET /api/health

System health check.

**Response:**
```json
{
  "status": "healthy",
  "version": "7.0.0",
  "components": {
    "database": "connected",
    "scheduler": "running",
    "event_bus": "active"
  },
  "timestamp": "2026-08-01T00:00:00Z"
}
```

### GET /api/system/status

Detailed system status.

**Response:**
```json
{
  "system": "operational",
  "uptime": 86400,
  "memory_usage": "2.5GB",
  "active_agents": 5,
  "queued_tasks": 12
}
```

## User Management

### POST /api/auth/register

Register new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "device_type": "desktop",
  "device_name": "My Device"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": "user_123",
  "token": "jwt_token_here"
}
```

### POST /api/auth/login

User login.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "device_type": "desktop",
  "device_name": "My Device"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": "user_123",
  "token": "jwt_token_here",
  "session_expires": "2026-08-02T00:00:00Z"
}
```

### POST /api/auth/logout

User logout.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

## Core Operations

### POST /api/opportunities/discover

Discover new opportunities.

**Request:**
```json
{
  "target": "example.com",
  "platform": "hackerone",
  "depth": 3
}
```

**Response:**
```json
{
  "success": true,
  "opportunities": [
    {
      "id": "opp_123",
      "title": "XSS in search endpoint",
      "severity": "high",
      "expected_value": 5000
    }
  ]
}
```

### POST /api/opportunities/validate

Validate an opportunity.

**Request:**
```json
{
  "opportunity_id": "opp_123",
  "hypothesis": "Search endpoint vulnerable to XSS"
}
```

**Response:**
```json
{
  "success": true,
  "validated": true,
  "evidence": "Base64 encoded evidence"
}
```

### POST /api/reports/generate

Generate vulnerability report.

**Request:**
```json
{
  "opportunity_id": "opp_123",
  "format": "pdf"
}
```

**Response:**
```json
{
  "success": true,
  "report_id": "report_456",
  "download_url": "/api/reports/report_456.pdf"
}
```

## Agent Operations

### GET /api/agents/status

Get agent fleet status.

**Response:**
```json
{
  "agents": [
    {
      "id": "agent_1",
      "name": "Security Analyst",
      "status": "working",
      "current_task": "Analyzing endpoint",
      "efficiency": 0.92
    }
  ]
}
```

### POST /api/agents/deploy

Deploy new agent.

**Request:**
```json
{
  "agent_type": "security_analyst",
  "target": "example.com",
  "priority": "high"
}
```

**Response:**
```json
{
  "success": true,
  "agent_id": "agent_2",
  "status": "deployed"
}
```

### POST /api/agents/terminate

Terminate running agent.

**Request:**
```json
{
  "agent_id": "agent_1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Agent terminated"
}
```

## MERLIN Assistant

### POST /api/merlin/chat

Chat with MERLIN assistant.

**Request:**
```json
{
  "message": "What vulnerabilities exist in example.com?",
  "context": "security_analysis"
}
```

**Response:**
```json
{
  "success": true,
  "response": "Based on analysis, I found 3 potential vulnerabilities...",
  "memory_used": true,
  "confidence": 0.87
}
```

### GET /api/merlin/memory

Get MERLIN memory.

**Response:**
```json
{
  "memories": [
    {
      "id": "mem_1",
      "content": "example.com has XSS vulnerability",
      "timestamp": "2026-08-01T00:00:00Z"
    }
  ]
}
```

## Scheduler

### GET /api/scheduler/jobs

List scheduled jobs.

**Response:**
```json
{
  "jobs": [
    {
      "id": "job_1",
      "name": "Daily scan",
      "schedule": "0 9 * * *",
      "status": "active",
      "next_run": "2026-08-02T09:00:00Z"
    }
  ]
}
```

### POST /api/scheduler/jobs

Create scheduled job.

**Request:**
```json
{
  "name": "Weekly scan",
  "schedule": "0 9 * * 1",
  "task": "discover",
  "target": "example.com"
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "job_2",
  "status": "scheduled"
}
```

### DELETE /api/scheduler/jobs/{job_id}

Delete scheduled job.

**Response:**
```json
{
  "success": true,
  "message": "Job deleted"
}
```

## System Configuration

### GET /api/config

Get system configuration.

**Response:**
```json
{
  "version": "7.0.0",
  "environment": "development",
  "features": {
    "merlin_enabled": true,
    "scheduler_enabled": true,
    "auto_update": false
  }
}
```

### PUT /api/config

Update system configuration.

**Request:**
```json
{
  "features": {
    "merlin_enabled": true,
    "auto_update": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated"
}
```

## Data & Analytics

### GET /api/analytics/revenue

Get revenue analytics.

**Response:**
```json
{
  "total_revenue": 15000,
  "monthly_revenue": 2500,
  "platform_breakdown": {
    "hackerone": 10000,
    "bugcrowd": 5000
  }
}
```

### GET /api/analytics/performance

Get performance metrics.

**Response:**
```json
{
  "agent_efficiency": 0.87,
  "validation_rate": 0.72,
  "acceptance_rate": 0.65,
  "avg_response_time": 48
}
```

## Error Responses

All endpoints may return error responses:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": "Additional error details"
}
```

### Common Error Codes

- `AUTH_REQUIRED`: Authentication required
- `INVALID_TOKEN`: Invalid or expired token
- `PERMISSION_DENIED`: Insufficient permissions
- `RESOURCE_NOT_FOUND`: Requested resource not found
- `VALIDATION_ERROR`: Request validation failed
- `RATE_LIMIT_EXCEEDED`: Rate limit exceeded
- `INTERNAL_ERROR`: Internal server error

## Rate Limiting

API calls are rate limited:
- Free tier: 100 requests/minute
- Pro tier: 1000 requests/minute
- Enterprise: Unlimited

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1627845600
```

## Webhooks

Configure webhooks for real-time notifications:

### POST /api/webhooks

Create webhook.

**Request:**
```json
{
  "url": "https://your-domain.com/webhook",
  "events": ["opportunity_found", "report_generated"],
  "secret": "webhook_secret"
}
```

**Response:**
```json
{
  "success": true,
  "webhook_id": "webhook_1"
}
```

## SDK Examples

### Python

```python
import requests

# Initialize client
client = requests.Session()
client.headers.update({
    "Authorization": "Bearer YOUR_API_KEY"
})

# Get health
response = client.get("http://127.0.0.1:8000/api/health")
print(response.json())

# Discover opportunities
response = client.post("http://127.0.0.1:8000/api/opportunities/discover", json={
    "target": "example.com",
    "platform": "hackerone"
})
print(response.json())
```

### JavaScript

```javascript
// Initialize client
const client = {
  baseUrl: 'http://127.0.0.1:8000',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY'
  }
};

// Get health
async function getHealth() {
  const response = await fetch(`${client.baseUrl}/api/health`, {
    headers: client.headers
  });
  return await response.json();
}

// Discover opportunities
async function discoverOpportunities(target) {
  const response = await fetch(`${client.baseUrl}/api/opportunities/discover`, {
    method: 'POST',
    headers: client.headers,
    body: JSON.stringify({ target, platform: 'hackerone' })
  });
  return await response.json();
}
```

---

**Last Updated:** 2026-08-01
**Version:** 7.0.0
