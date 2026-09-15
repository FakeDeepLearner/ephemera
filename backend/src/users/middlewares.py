import os
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse
import jwt
from jwt import PyJWKClient

from .models import User


class ClerkAuthenticationMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Perform authentication logic here
        # For example, you can check for a token in the request headers
        token = self.get_request_auth_token(request)
        if not token:
            return HttpResponse("Unauthorized", status=401)
        # In a real-world scenario, you would validate the token here
        # For example, you could check if the token is in a list of valid tokens
        if not (claims := self.verify_token(token)):
            return HttpResponse("Unauthorized", status=401)

        claim_subject = claims["sub"]

        found_user = User.objects.get(clerk_id=claim_subject)
        if not found_user:
            return HttpResponse("Unauthorized", status=401)

        request.user = found_user  # Attach the user to the request for later use
        # If the token is valid, proceed to the next middleware or view
        response = self.get_response(request)
        return response

    def get_request_auth_token(self, request: HttpRequest) -> str | None:
        """Extract the authentication token from the request headers."""
        return request.headers.get("Authorization")

    def verify_token(self, token: str) -> dict[str, Any] | None:
        """Verify the JWT token and return the decoded payload if valid."""
        try:
            # Replace 'your-public-key' with your actual public key or use a JWKS endpoint
            jwks_url = os.environ["CLERK_JWKS_URL"]
            jwks_client = PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            decoded_token_claims = jwt.decode(token, signing_key.key, algorithms=["RS256"])
            return decoded_token_claims
        except Exception as e:
            print(f"Token verification failed: {e}")
            return None