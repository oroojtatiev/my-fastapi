from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = Path(__file__).resolve().parent / ".env"

class Settings(BaseSettings):
  model_config = SettingsConfigDict(
    env_file=env_file,
    extra="ignore",
  )

  database_url: str

  frontend_url: str

  auth_secret_key: SecretStr
  auth_algorithm: str
  auth_access_token_expire_minutes: int

  media_profile_pics_dir: Path
  media_default_profile_pic: Path
  media_max_upload_size_bytes: int = 5 * 1024 * 1024 # 5mb

  mail_reset_token_expire_minutes: int
  mail_server: str
  mail_port: int
  mail_username: str
  mail_password: SecretStr
  mail_from: str
  mail_use_tls: bool = True

  s3_bucket_name: str
  s3_region: str = "eu-north-1"
  s3_access_key_id: SecretStr | None = None
  s3_secret_access_key: SecretStr | None = None
  s3_endpoint_url: str | None = None


settings = Settings()
