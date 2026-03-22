import json
import os
from contextlib import asynccontextmanager
from datetime import datetime

import stripe
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import (
    create_access_token,
    get_active_subscriber,
    get_current_user,
    hash_password,
    verify_password,
)
from .database import get_db, init_db
from .models import ScanRun, User
from .scraper import run_scan

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
APP_URL = os.environ.get("APP_URL", "http://localhost:8000")

scheduler = AsyncIOScheduler()


async def daily_scan_job():
    """Runs every day at 07:00 to refresh listings."""
    from .database import SessionLocal

    try:
        listings = run_scan(top_n=50)
        async with SessionLocal() as db:
            run = ScanRun(
                listings_json=json.dumps(listings),
                listing_count=len(listings),
                is_demo=False,
            )
            db.add(run)
            await db.commit()
    except Exception as e:
        print(f"[scheduler] scan failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.add_job(daily_scan_job, "cron", hour=7, minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="CarScan IDF", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Auth ────────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@app.post("/auth/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(user.id, user.email)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id, user.email)
    return {"access_token": token, "token_type": "bearer"}


# ─── User info ───────────────────────────────────────────────────────────────


@app.get("/api/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "subscription_status": user.subscription_status,
    }


# ─── Stripe ──────────────────────────────────────────────────────────────────


@app.post("/stripe/create-checkout-session")
async def create_checkout_session(user: User = Depends(get_current_user)):
    if user.subscription_status == "active":
        raise HTTPException(status_code=400, detail="Already subscribed")

    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        mode="subscription",
        success_url=f"{APP_URL}/dashboard.html?subscribed=1",
        cancel_url=f"{APP_URL}/pricing.html",
        metadata={"user_id": str(user.id)},
    )
    return {"url": session.url}


@app.post("/stripe/create-portal-session")
async def create_portal_session(user: User = Depends(get_current_user)):
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{APP_URL}/dashboard.html",
    )
    return {"url": session.url}


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")
        user_id = int(session.get("metadata", {}).get("user_id", 0))
        subscription_id = session.get("subscription")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.stripe_customer_id = customer_id
            user.stripe_subscription_id = subscription_id
            user.subscription_status = "active"
            await db.commit()

    elif event["type"] in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        stripe_status = sub.get("status")  # active, past_due, canceled, etc.
        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.subscription_status = "active" if stripe_status == "active" else stripe_status or "inactive"
            await db.commit()

    return {"ok": True}


# ─── Listings API ────────────────────────────────────────────────────────────


@app.get("/api/listings")
async def get_listings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns listings from the latest scan.
    - Subscribers: full top 50
    - Free users: teaser (top 3, prices and links hidden)
    """
    result = await db.execute(
        select(ScanRun).order_by(ScanRun.run_at.desc()).limit(1)
    )
    scan = result.scalar_one_or_none()

    if not scan:
        return {"listings": [], "scan_at": None, "total": 0, "subscribed": False}

    listings = json.loads(scan.listings_json)
    subscribed = user.subscription_status == "active"

    if not subscribed:
        # Teaser: show only top 3, blur sensitive data
        teaser = []
        for car in listings[:3]:
            teaser.append({
                "title": car["title"],
                "year": car["year"],
                "fuel": car["fuel"],
                "location": car["location"],
                "roi_score": car["roi_score"],
                "roi_reasons": car["roi_reasons"][:2],
                "price": "???",
                "estimated_profit": "???",
                "url": None,
            })
        return {
            "listings": teaser,
            "scan_at": scan.run_at.isoformat(),
            "total": len(listings),
            "subscribed": False,
        }

    return {
        "listings": listings,
        "scan_at": scan.run_at.isoformat(),
        "total": len(listings),
        "subscribed": True,
    }


@app.get("/api/scan-status")
async def scan_status(db: AsyncSession = Depends(get_db)):
    """Public — returns last scan time and listing count."""
    result = await db.execute(
        select(ScanRun).order_by(ScanRun.run_at.desc()).limit(1)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        return {"last_scan": None, "count": 0}
    return {"last_scan": scan.run_at.isoformat(), "count": scan.listing_count}


# ─── Static files / SPA ──────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
