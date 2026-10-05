from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    doskaz_base_url: str = "https://doskaz.kz"
    doskaz_access_token: str
    admin_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()

'''Reads the .env file into a typed object. doskaz_access_token is the one shared account's token from the setup section above; admin_api_key guards the admin-only routes built in phase 7. Every doskaz-facing or admin-facing call in this guide reads its credential from here.'''