"""
YottaFlex.ai Compensation Equity Analyzer - Configuration
Centralized configuration management for database, business logic, seeds, and security.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = BASE_DIR / "database"
DOCS_DIR = BASE_DIR / "documentation"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    # Application Info
    APP_NAME: str = "Compensation Equity Analyzer"
    APP_SUBTITLE: str = "AI-Powered Salary Disparity Detection System"
    APP_VERSION: str = "2.4.0"
    COMPANY_NAME: str = "YottaFlex.ai"
    DEBUG: bool = False

    # Seed & Reproducibility
    RANDOM_SEED: int = 20261022

    # Database Configuration
    # Defaults to SQLite if MySQL is unavailable
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "compensation_equity")
    USE_MYSQL: bool = os.getenv("USE_MYSQL", "false").lower() in ("true", "1", "yes")

    SQLITE_PATH: Path = DATABASE_DIR / "compensation_equity.db"

    @property
    def DATABASE_URL(self) -> str:
        if self.USE_MYSQL:
            return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        return f"sqlite:///{self.SQLITE_PATH.as_posix()}"

    # Business Logic Defaults
    BASE_CURRENCY: str = "USD"
    MAX_SALARY_HISTORY_MONTHS: int = 36
    HISTORY_START_DATE: str = "2024-01-01"
    HISTORY_END_DATE: str = "2026-12-31"

    # Compensation Thresholds
    COMPA_RATIO_LOW_THRESHOLD: float = 80.0
    COMPA_RATIO_HIGH_THRESHOLD: float = 120.0
    DISPARITY_PERCENT_FLAG: float = 15.0  # Percent deviation from peer median that triggers review
    DISPARITY_ZSCORE_FLAG: float = 1.8    # Statistical outlier z-score

    # User Roles
    ROLE_EMPLOYEE: str = "Employee"
    ROLE_MANAGER: str = "Manager"
    ROLE_HR_PARTNER: str = "HR Partner"
    ROLE_IT_OPS: str = "IT/Operations Partner"
    ROLE_ADMIN: str = "System Administrator"

settings = Settings()
