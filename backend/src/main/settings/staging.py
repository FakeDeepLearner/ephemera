from .base import *  # noqa: F403, F401

import os
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qsl, ParseResult

load_dotenv()

# Replace the DATABASES section of your settings.py with this
tmpPostgres: ParseResult = urlparse(os.environ['DATABASE_URL'])

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': tmpPostgres.path.replace('/', ''),
        'USER': tmpPostgres.username,
        'PASSWORD': tmpPostgres.password,
        'HOST': tmpPostgres.hostname,
        'PORT': tmpPostgres.port or 5432,
        'OPTIONS': dict(parse_qsl(tmpPostgres.query)),
        'ATOMIC_REQUESTS': True,
    }
}