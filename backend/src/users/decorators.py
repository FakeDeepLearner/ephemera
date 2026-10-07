from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar


View = TypeVar('View', bound=Callable[..., Any])


def clerk_auth_exempt(view: View) -> View:
    setattr(view, 'clerk_auth_exempt', True)
    return view
