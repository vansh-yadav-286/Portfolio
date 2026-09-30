from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    frontend_url: str = "http://localhost:5500"
    admin_email: str
    admin_password: str

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


settings = Settings()
