from dotenv import load_dotenv, dotenv_values
import os
from db import SessionLocal
from models import ServiceConfig

# Load environment variables from .env
load_dotenv()

class Settings:
    """
    Load key-value pairs from .env into attributes
    """
    def __init__(self, dotenv_path: str = ".env"):
        self._config = dotenv_values(dotenv_path)
        for key, value in self._config.items():
            setattr(self, key, value)

    def dict(self):
        return self._config

# Instantiate settings
settings = Settings()

# Prepare list of ServiceConfig objects from .env entries (excluding DATABASE_URL)
SERVICE_CONFIGS = [
    ServiceConfig(service_name=key, config_json=value)
    for key, value in settings.dict().items()
    if key.upper() != "DATABASE_URL"
]

def init_service_configs():
    """
    Insert SERVICE_CONFIGS into database if not already present
    """
    session = SessionLocal()
    for sc in SERVICE_CONFIGS:
        exists = session.query(ServiceConfig).filter_by(service_name=sc.service_name).first()
        if not exists:
            session.add(sc)
    session.commit()
    session.close()

if __name__ == "__main__":
    # Initialize DB tables and seed service_configs
    from db import init_db

    init_db()
    init_service_configs()
    # Print service names from .env settings instead of detached ORM instances
    service_names = [key for key in settings.dict().keys() if key.upper() != "DATABASE_URL"]
    print("Service configs initialized:", service_names)