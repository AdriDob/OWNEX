# OWNEX v5.1.0 - Windows 11 Installation Guide

## Prerequisites

1. **Python 3.11+** installed and in PATH
   - Download: https://www.python.org/downloads/
   - Check: `python --version`

2. **Git** installed
   - Check: `git --version`

## Quick Install (PowerShell as Admin)

```powershell
# 1. Clone the repo
git clone https://github.com/OWNEX/rastro.git
cd rastro

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.venv\Scripts\activate

# 4. Install dependencies
pip install -e .

# 5. Start OWNEX
python -m api.main
```

## Access the API

Once running, the API is at:
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/health
- **OpenAPI**: http://localhost:8000/openapi.json

## Troubleshooting

If you get port already in use:
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process
```

If Python is not recognized, use full path to Python installation.