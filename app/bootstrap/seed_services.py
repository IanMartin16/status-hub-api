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
]


def seed_services(db: Session) -> None:
    for item in DEFAULT_SERVICES:
        exists = db.query(Service).filter(Service.name == item["name"]).first()
        if not exists:
            db.add(Service(**item))
    db.commit()