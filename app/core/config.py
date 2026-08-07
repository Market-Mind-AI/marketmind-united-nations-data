from urllib.parse import quote

from pydantic_settings import BaseSettings

from app.db.ssl_config import sslmode_query_suffix


class Settings(BaseSettings):
    app_name: str = "marketmind-united-nations-data"
    app_env: str = "local"
    app_port: int = 8000
    app_version: str = "0.2.0"

    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "marketmind_united_nations_data"
    database_user: str = "marketmind"
    database_password: str = "marketmind_password"

    # TLS for the Postgres connection. "disable" keeps local docker-compose
    # working unchanged; Azure Database for PostgreSQL Flexible Server needs at
    # least "require" because it refuses plaintext connections
    # (`require_secure_transport = ON`). See app/db/ssl_config.py.
    database_ssl_mode: str = "disable"

    undata_api_base_url: str = "https://population.un.org/dataportalapi/uiapi/v1"

    default_timeout: int = 60
    # Raised 3 -> 5: the UN Data Portal API throws intermittent 5xx/timeouts
    # under load; extra attempts absorb transient blips so a single failure
    # does not drop an indicator and abort a downstream MarketMind analysis.
    default_retries: int = 5
    default_backoff: int = 2

    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def database_url(self) -> str:
        # psycopg2 reads `sslmode` straight off the DSN.
        return (
            f"postgresql://{self.database_user}:{quote(self.database_password, safe='')}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
            f"{sslmode_query_suffix(self.database_ssl_mode)}"
        )


settings = Settings()
