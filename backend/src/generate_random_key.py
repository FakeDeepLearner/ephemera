# A short script used to generate the secret keys for the local, staging, and production environments.

from django.core.management.utils import get_random_secret_key

print(get_random_secret_key())