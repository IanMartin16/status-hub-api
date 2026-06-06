from sqlalchemy.orm import Session
from app.models.service import Service


DEFAULT_SERVICES = [
    {
        "name": "cryptolink-api",
        "display_name": "CryptoLink API",
        "health_url": "https://cryptolink-production.up.railway.app/actuator/health",
        "category": "core",
        "is_active": True,
    },
    {
        "name": "curpify-api",
        "display_name": "Curpify API",
        "health_url": "https://curp-api-production.up.railway.app/api/health",
        "category": "core",
        "is_active": True,
    },
    {
        "name": "nexus-api",
        "display_name": "Nexus API",
        "health_url": "https://nexus-api-production-7492.up.railway.app/health",
        "category": "core",
        "is_active": True,
    },
    {
        "name": "social-link",
        "display_name": "Social_Link API",
        "health_url": "https://social-link-production.up.railway.app/health",
        "category": "core",
        "is_active": True,
    },
    {
        "name": "data-link",
        "display_name": "Data_Link API",
        "health_url": "https://data-link-api-production.up.railway.app/health",
        "category": "core",
        "is_active": True,
    },
    {
        "name": "V-secrets",
        "display_name": "V-Secrets API",
        "health_url": "https://v-secrets-api-production.up.railway.app/health/readiness",
        "category": "core",
        "is_active": True,
    },
    {
        "name": "mcp-one",
        "display_name": "MCPOne API",
        "health_url": "https://mcp-one-production.up.railway.app/health",
        "category": "core",
        "is_active": True,
    },
]


def seed_services(db: Session) -> None:
    for item in DEFAULT_SERVICES:
        exists = db.query(Service).filter(Service.name == item["name"]).first()
        if not exists:
            db.add(Service(**item))
    db.commit()