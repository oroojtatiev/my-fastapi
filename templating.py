from pathlib import Path

from fastapi.templating import Jinja2Templates

from config import DEFAULT_PROFILE_PIC_KEY, s3_public_url

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["default_profile_pic_url"] = s3_public_url(DEFAULT_PROFILE_PIC_KEY)
