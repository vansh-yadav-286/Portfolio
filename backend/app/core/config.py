from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Signs the session cookie and the OAuth `state` parameter. There is no
    # database, so this secret is the only thing standing behind "this visitor
    # is who they claim to be" - treat it like a password.
    session_secret: str
    session_max_age_minutes: int = 120

    frontend_url: str = "http://localhost:5500"
    admin_email: str

    # Public URL of this backend, used to build OAuth callback URLs
    # (e.g. https://portfolio-api-xxxx.onrender.com in production).
    backend_url: str = "http://localhost:8000"

    # OAuth credentials. Left blank, the corresponding provider's login route
    # responds with 503 instead of crashing on startup.
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    # Contact form -> outbound email (SMTP). Left blank, POST /api/contact
    # responds with 503 instead of silently discarding the message.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    contact_email_to: str = ""
    contact_email_from: str = ""

    @property
    def frontend_origins(self) -> list[str]:
        # FRONTEND_URL can list several origins, comma-separated, e.g.
        # "https://<project>.vercel.app,http://localhost:5500". Never "*" -
        # required for credentialed (cookie) cross-origin requests to work at all.
        return [origin.strip().rstrip("/") for origin in self.frontend_url.split(",") if origin.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.contact_email_to and self.contact_email_from)


settings = Settings()
