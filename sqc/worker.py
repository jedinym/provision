import os
from typing import Any

from loguru import logger
from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin

from sqc.repository import MinioRepo, SQCResponse
from sqc.validation import ValidationError, Validator


class Worker(ConsumerMixin):
    queue = Queue("requests", Exchange("requests", type="fanout", durable=True), "#")

    def __init__(self, repo: MinioRepo) -> None:
        rabbit_url = os.environ.get("RABBIT_URL", "amqp://guest:guest@localhost:5672//")
        self.connection = Connection(rabbit_url)
        self.repo = repo

    def get_consumers(self, consumer, _channel):
        return [consumer(queues=[self.queue], callbacks=[self.on_message])]

    def on_message(self, body: dict[str, Any], message) -> None:
        message.ack()

        if (event_name := body["EventName"]) != "s3:ObjectCreated:Put":
            logger.warning(f"Invalid event name: {event_name}, dropping message")
            return

        request = body["Records"][0]["s3"]["object"]["key"]
        logger.info(f"Got request: {request}")

        resp: SQCResponse | None = None
        try:
            path = self.repo.download_request(request)
            result = Validator.validate(path)
            resp = SQCResponse.ok(result)
        except ValidationError as err:
            resp = SQCResponse.err(str(err))
        finally:
            if resp:
                self.repo.write_response(request, resp)

    def run(self, *args, **kwargs) -> None:
        while not self.should_stop:
            with logger.catch():
                super().run(*args, **kwargs)
            self.connection.release()
