from django.db.transaction import atomic

from .base import *
from dotenv import load_dotenv
DEBUG = True

load_dotenv()
default_config = dj_database_url.config(default=os.environ["DATABASE_URL"],
                                        conn_max_age = 600,
                                        conn_health_checks= True)

#Makes every request atomic, so if an exception occurs, the transaction will be rolled back.
default_config["ATOMIC_REQUESTS"] = True

DATABASES = {
    'default': default_config
}