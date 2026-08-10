# Deployment Guide — OWNEX OMEGA

Guía rápida de deployment para OWNEX OMEGA v7.0.0.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (opcional)
- Supabase account (gratuito)

## Step 1: Configurar Supabase

1. Crea proyecto en https://supabase.com
2. Obtén Project URL y anon key
3. Ejecuta schema SQL en Supabase SQL Editor

```bash
python scripts/setup_supabase.py
```

## Step 2: Configurar Environment Variables

```bash
# Backend
cp .env.example .env
# Editar .env con tus credenciales
# Agregar: SUPABASE_URL, SUPABASE_KEY

# Frontend
cd frontend
cp .env.example .env
# Editar .env con tus credenciales
# Agregar: VITE_SUPABASE_URL, VITE_SUPABASE_KEY
```

## Step 3: Instalar Dependencias

```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

## Step 4: Ejecutar Localmente

```bash
# Backend (Terminal 1)
source .venv/bin/activate
python api/main.py

# Frontend (Terminal 2)
cd frontend
npm run dev
```

## Step 5: Deployment en Producción

### Backend (FastAPI + Uvicorn)

```bash
# Using gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Using systemd
sudo nano /etc/systemd/system/ownex-omega.service
```

```ini
[Unit]
Description=OWNEX OMEGA Backend
After=network.target

[Service]
User=your-user
WorkingDirectory=/path/to/Rastro
Environment="PATH=/path/to/Rastro/.venv/bin"
ExecStart=/path/to/Rastro/.venv/bin/gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ownex-omega
sudo systemctl start ownex-omega
```

### Frontend (Vite + Nginx)

```bash
cd frontend
npm run build
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/Rastro/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker (Opcional)

```bash
docker build -t ownex-omega:latest .
docker run -d -p 8000:8000 -p 5173:5173 ownex-omega:latest
```

## Step 6: SSL/HTTPS

```bash
sudo certbot --nginx -d your-domain.com
```

## Step 7: Monitoring

Configure health checks:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/system/status
```

## Troubleshooting

### Backend no inicia
- Verifica que puerto 8000 esté libre
- Verifica environment variables
- Revisa logs: `journalctl -u ownex-omega -f`

### Frontend no carga
- Verifica que backend esté corriendo
- Verifica configuración de Nginx
- Revisa logs de Nginx: `sudo tail -f /var/log/nginx/error.log`

### Supabase no conecta
- Verifica credenciales en .env
- Verifica que schema SQL se ejecutó
- Revisa logs de backend

---

**Más información:** README.md, SUPABASE_SETUP_GUIDE.md
