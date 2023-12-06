from asyncio import sleep
import grpclib

from endpoint import ValidationEndpointBase, ValidationRequest, RequestId

class EndpointService(ValidationEndpointBase):
    async def validate(self, validation_request: "ValidationRequest") -> "RequestId":
        pass
