# OWNEX Troubleshooting Guide

Common issues and solutions for OWNEX Autonomous Personal Operating System.

## Installation Issues

### Python Environment Setup

**Issue:** `ModuleNotFoundError` after installation
```bash
# Solution: Ensure virtual environment is activated
source .venv/bin/activate
pip install -r requirements.txt
```

**Issue:** Permission denied during installation
```bash
# Solution: Use user-level installation
pip install --user -r requirements.txt
```

### Frontend Dependencies

**Issue:** `npm install` fails with network errors
```bash
# Solution: Clear npm cache and retry
npm cache clean --force
npm install
```

**Issue:** TypeScript errors in frontend
```bash
# Solution: Regenerate type definitions
cd frontend
npm run type-check
```

## Runtime Issues

### Backend Startup

**Issue:** Backend fails to start on port 8000
```bash
# Solution: Check if port is in use
lsof -i :8000
# Kill existing process or change port in api/main.py
```

**Issue:** Database connection errors
```bash
# Solution: Initialize database
python run.py --init-db
# Check .env configuration
cat .env | grep DATABASE
```

### Frontend Connection

**Issue:** Frontend cannot connect to backend
```bash
# Solution: Verify backend is running
curl http://127.0.0.1:8000/api/health
# Check frontend .env configuration
cat frontend/.env | grep VITE_API_URL
```

**Issue:** CORS errors in browser console
```bash
# Solution: Check CORS configuration in api/main.py
# Ensure allowed origins include frontend URL
```

## Mobile Issues

### Android Build

**Issue:** Gradle build fails
```bash
# Solution: Clean and rebuild
cd android
./gradlew clean
./gradlew build
```

**Issue:** Android namespace errors
```bash
# Solution: Install Java JDK and update namespace
sudo apt install openjdk-17-jdk
# Update applicationId in android/app/build.gradle
```

### Supabase Configuration

**Issue:** Supabase connection fails
```bash
# Solution: Verify Supabase credentials
cat frontend/.env | grep SUPABASE
# Test connection with Supabase dashboard
```

## Performance Issues

### Backend Performance

**Issue:** Slow API response times
```bash
# Solution: Check database queries
python run.py --profile-db
# Enable query logging in api/main.py
```

**Issue:** Memory usage too high
```bash
# Solution: Check for memory leaks
python run.py --memory-profile
# Restart services periodically
```

### Frontend Performance

**Issue:** Slow page loads
```bash
# Solution: Build production version
cd frontend
npm run build
# Enable lazy loading for components
```

## Integration Issues

### MERLIN Assistant

**Issue:** MERLIN not responding
```bash
# Solution: Check AI model availability
python run.py --check-models
# Verify API keys in .env
```

**Issue:** Memory not persisting
```bash
# Solution: Check unified memory configuration
python run.py --check-memory
# Ensure database has write permissions
```

### Scheduler

**Issue:** Scheduled tasks not running
```bash
# Solution: Check scheduler status
python run.py --scheduler-status
# Verify cron configuration
python run.py --list-jobs
```

## Debugging

### Enable Debug Mode

```bash
# Backend debug mode
python api/main.py --debug

# Frontend debug mode
cd frontend
npm run dev -- --debug
```

### Check Logs

```bash
# Backend logs
tail -f logs/api.log

# Frontend logs (browser console)
# Open Developer Tools → Console

# System logs
tail -f logs/system.log
```

### Health Checks

```bash
# System health
curl http://127.0.0.1:8000/api/health

# Database health
python run.py --health-db

# Scheduler health
python run.py --health-scheduler
```

## Common Error Messages

### `ImportError: No module named 'X'`
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`
- Check Python version compatibility

### `Connection refused`
- Verify backend is running
- Check port configuration
- Test with `curl` command

### `Authentication failed`
- Verify API keys in `.env`
- Check Supabase credentials
- Ensure tokens are not expired

### `Database locked`
- Check for other processes using database
- Restart database service
- Use `--force-unlock` flag if available

## Recovery Procedures

### System Backup

```bash
# Create backup before major changes
python run.py --backup

# Restore from backup
python run.py --restore <backup-file>
```

### Reset Configuration

```bash
# Reset to default configuration
python run.py --reset-config

# Re-initialize database
python run.py --init-db --force
```

### Clean Installation

```bash
# Remove all generated files
python run.py --clean

# Fresh installation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py --init
```

## Getting Help

### Check Documentation
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Complete documentation index
- [QUICK_START.md](QUICK_START.md) - Quick start guide
- [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) - Architecture decisions

### System Status
```bash
# Full system status
python run.py --status

# Component status
python run.py --status-backend
python run.py --status-frontend
python run.py --status-mobile
```

### Create Issue
Use [GitHub Issue Template](.github/ISSUE_TEMPLATE/bug_report.md) to report bugs with:
- Environment details
- Error messages
- Steps to reproduce
- Expected vs actual behavior

## Emergency Procedures

### Emergency Shutdown
```bash
# Stop all services
python run.py --stop-all

# Force kill processes
pkill -f "python api/main.py"
pkill -f "npm run dev"
```

### Data Recovery
```bash
# Emergency backup
python run.py --emergency-backup

# Data integrity check
python run.py --check-integrity
```

### System Reset
```bash
# Full system reset (use with caution)
python run.py --factory-reset
```

---

**Last Updated:** 2026-08-01
**Version:** 7.0.0
