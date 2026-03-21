# CarScan IDF — Déploiement VPS

## Prérequis

- VPS avec Docker + Docker Compose installés (Ubuntu 22.04 recommandé)
- Domaine pointé sur l'IP du VPS
- Compte Stripe (stripe.com)

## 1. Configuration Stripe

1. Créer un compte sur [stripe.com](https://stripe.com)
2. Créer un **Produit** : "CarScan IDF"
3. Créer un **Prix** : récurrent, 5,00€/mois, EUR
4. Copier le `price_...` ID
5. Dans **Développeurs → Clés API** : copier `sk_live_...`
6. Dans **Développeurs → Webhooks** → Ajouter un endpoint :
   - URL : `https://yourdomain.com/stripe/webhook`
   - Événements : `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Copier le `whsec_...` secret

## 2. Déploiement

```bash
# Sur le VPS
git clone <votre-repo> carscan
cd carscan/saas

# Copier et remplir la config
cp .env.example .env
nano .env   # remplir toutes les valeurs CHANGE_ME

# Lancer
docker compose up -d --build

# Vérifier
docker compose logs -f web
```

## 3. HTTPS avec Nginx + Certbot

```bash
# Installer nginx et certbot
apt install nginx certbot python3-certbot-nginx -y

# Config nginx /etc/nginx/sites-available/carscan
server {
    server_name yourdomain.com;
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

ln -s /etc/nginx/sites-available/carscan /etc/nginx/sites-enabled/
certbot --nginx -d yourdomain.com
systemctl reload nginx
```

## 4. Premier scan manuel (optionnel)

Le scan automatique tourne chaque matin à 7h. Pour forcer un premier scan :

```bash
docker compose exec web python3 -c "
from app.scraper import run_scan
import json, asyncio
from app.database import SessionLocal
from app.models import ScanRun

listings = run_scan(top_n=50)
async def save():
    async with SessionLocal() as db:
        db.add(ScanRun(listings_json=json.dumps(listings), listing_count=len(listings)))
        await db.commit()
        print(f'Saved {len(listings)} listings')
asyncio.run(save())
"
```

## Architecture

```
Client (browser)
    ↓
nginx (HTTPS, port 443)
    ↓
FastAPI uvicorn (port 8000)
    ├── /auth/*        → inscription / connexion JWT
    ├── /api/*         → listings, user info
    ├── /stripe/*      → checkout, webhook, portal
    └── /*             → fichiers statiques frontend
    ↓
PostgreSQL (port 5432, interne Docker)

APScheduler (interne FastAPI) → scrape leboncoin chaque matin 7h
```
