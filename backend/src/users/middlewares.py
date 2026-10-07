from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import jwt
from django.http import HttpRequest, HttpResponse
from django.urls import Resolver404, resolve
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from .models import User


def get_request_auth_token(request: HttpRequest) -> str | None:
    authorization = request.headers.get('Authorization')
    if not authorization:
        return None

    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        return None
    return token.strip() or None


def is_authentication_exempt(request: HttpRequest) -> bool:
    try:
        resolved = resolve(request.path_info)
    except Resolver404:
        return False
    return bool(getattr(resolved.func, 'clerk_auth_exempt', False))


def verify_token(token: str) -> dict[str, Any] | None:
    try:
        jwks_url = os.environ['CLERK_JWKS_URL']
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=['RS256'],
        )
    except (KeyError, InvalidTokenError, PyJWKClientError):
        return None

    return claims


class ClerkAuthenticationMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if is_authentication_exempt(request):
            return self.get_response(request)

        token = get_request_auth_token(request)
        if token is None:
            return HttpResponse('Unauthorized', status = 401)

        claims = verify_token(token)
        if claims is None:
            return HttpResponse('Unauthorized', status = 401)

        claim_subject = claims.get('sub')
        if not isinstance(claim_subject, str) or not claim_subject:
            return HttpResponse('Unauthorized', status = 401)

        try:
            found_user = User.objects.get(clerk_id=claim_subject)
        except User.DoesNotExist:
            return HttpResponse('Unauthorized', status = 401)

        request.user = found_user
        return self.get_response(request)
