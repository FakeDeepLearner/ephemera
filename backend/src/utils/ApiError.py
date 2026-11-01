from rest_framework.exceptions import APIException


# Since this class extends APIException, it will be handled by the global exception
# handler in DRF and returned as a JSON response with the appropriate status code when it is raised.
class ApiError(APIException):
    detail: str
    status_code: int
    def __init__(self, message: str, status_code: int):
        super().__init__(detail = message, code = None)
        self.status_code = status_code