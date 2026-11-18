from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    doskaz_base_url: str = "https://doskaz.kz"
    doskaz_access_token: str
    admin_api_key: str
    doskaz_handoff_enabled: bool = False
    session_secret: str  # signs the staff login cookie; generate with: python -c "import secrets; print(secrets.token_hex(32))"
    session_https_only: bool = False  # set to true on the server (HTTPS), keep false for local http

    class Config:
        env_file = ".env"


settings = Settings()

'''Reads the .env file into a typed object. doskaz_access_token is the one shared account's token from the setup section above; admin_api_key guards the admin-only routes built in phase 7. Every doskaz-facing or admin-facing call in this guide reads its credential from here.'''