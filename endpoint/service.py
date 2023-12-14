from loguru import logger

from sqcapi import ValidationEndpointBase, ValidateRequest, ValidateResponse

from common.repo import StructRepository


class EndpointService(ValidationEndpointBase):
    def __init__(self, repo: StructRepository) -> None:
        super().__init__()
        self.repo = repo

    async def validate(
        self, validation_request: "ValidateRequest"
    ) -> "ValidateResponse":
        return ValidateResponse(request_id=42)
