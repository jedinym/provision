from sqcapi import ValidationEndpointBase, ValidateRequest, ValidateResponse


class EndpointService(ValidationEndpointBase):
    async def validate(
        self, validation_request: "ValidateRequest"
    ) -> "ValidateResponse":
        return ValidateResponse(request_id=42)
