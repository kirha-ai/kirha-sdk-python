from typing import Any


class KirhaError(Exception):
    pass


class ConfigurationError(KirhaError):
    pass


class ApiError(KirhaError):
    def __init__(
        self, message: str, status_code: int, code: str, details: Any = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.details = details


class AuthenticationError(ApiError):
    pass


class RateLimitError(ApiError):
    def __init__(
        self,
        message: str,
        status_code: int,
        code: str,
        details: Any = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, status_code, code, details)
        self.retry_after = retry_after


class PlanExpiredError(KirhaError):
    def __init__(self, plan_id: str) -> None:
        super().__init__(f"Plan {plan_id} has expired (plans are valid for 5 minutes)")
        self.plan_id = plan_id


class NetworkError(KirhaError):
    pass
