from dataclasses import dataclass
from http import HTTPStatus

@dataclass
class ApiError(Exception):
    status_code: HTTPStatus
    message: str
