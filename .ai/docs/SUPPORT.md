# Support

## Getting Help

### Documentation
- **README.md** - Quick start, installation, usage examples
- **docs/** - Comprehensive documentation
  - [Architecture](docs/architecture/)
  - [Development](docs/development/)
  - [Operations](docs/operations/)
  - [API Reference](docs/API_REFERENCE.md)

### Community Support
- **GitHub Discussions**: [Ask questions, share ideas](https://github.com/AdriDob/rastrohunteralpha/discussions)
- **GitHub Issues**: [Bug reports, feature requests](https://github.com/AdriDob/rastrohunteralpha/issues)
- **Discord**: [Real-time chat](https://discord.gg/ownex)

### Professional Support
- **Email**: support@ownex.ai
- **Consulting**: Available for enterprise integration

## Troubleshooting

### Common Issues

#### Installation Problems
```bash
# Clear and reinstall
rm -rf .venv node_modules
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install
```

#### Port Conflicts
```bash
# Check what's using ports 8000, 5173
lsof -i :8000
lsof -i :5173
```

#### Database Issues
```bash
# Reset database
rm database/catseye.db
python scripts/seed_database.py
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn api.main:app --reload --port 8000
```

## FAQ

### Q: Does OWNEX require internet access?
**A**: OWNEX works fully offline with local models (Ollama). Cloud AI providers are optional.

### Q: Can I run OWNEX on Windows?
**A**: Yes, via WSL2 or native Windows. See [Windows Setup](docs/development/WINDOWS_SETUP.md).

### Q: How do I contribute?
**A**: See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Q: Is OWNEX free?
**A**: Yes, MIT licensed. Commercial support available.

## Status & Health

### System Health Check
```bash
curl http://localhost:8000/api/health
```

### Service Status
```bash
# Check all services
python scripts/ownex_doctor.py
```

## Updates

### Stay Informed
- **Releases**: Watch this repository for releases
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Twitter**: [@ownex_ai](https://twitter.com/ownex_ai)

### Updating
```bash
git pull
pip install -r requirements.txt
cd frontend && npm install
```

## License

MIT License - see [LICENSE](LICENSE) for details.