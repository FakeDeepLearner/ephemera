from .base import *
from dotenv import load_dotenv
DEBUG = True

load_dotenv()
DATABASES = {
    'default': dj_database_url.config(
        default = os.environ['DATABASE_URL'],
        conn_max_age = 600,
        conn_health_checks = True
    )
}