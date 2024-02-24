import os
from typing import Any

from structlog import get_logger
import structlog
from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin

from sqc.repository import ConversionError, InternalError, MinioRepo, SQCResponse
from sqc.validation import ValidationError, Validator

logger = get_logger()


class Worker(ConsumerMixin):
    queue = Queue("requests", Exchange("requests", type="fanout", durable=True), "#")

    def __init__(self, repo: MinioRepo) -> None:
        rabbit_user = os.environ.get("RABBITMQ_USER", "guest")
        rabbit_password = os.environ.get("RABBITMQ_PASSWORD", "guest")
        rabbit_url = os.environ.get("RABBITMQ_URL", "rabbitmq:5672")
        rabbit_conn = f"amqp://{rabbit_user}:{rabbit_password}@{rabbit_url}//"
        self.connection = Connection(rabbit_conn)
        self.repo = repo

    def get_consumers(self, consumer, _):
        return [consumer(queues=[self.queue], callbacks=[self.on_message])]

    def on_message(self, body: dict[str, Any], message) -> None:
        message.ack()
        structlog.contextvars.clear_contextvars()

        if (event_name := body["EventName"]) != "s3:ObjectCreated:Put":
            logger.warning(f"Invalid event name: {event_name}, dropping message")
            return

        request = body["Records"][0]["s3"]["object"]["key"]
        structlog.contextvars.bind_contextvars(request_id=request)
        logger.info("Got new request")

        resp: SQCResponse | None = None
        try:
            path = self.repo.download_request(request)
            result = Validator.validate(path)
            resp = SQCResponse.ok(result)
        except (ValidationError, ConversionError) as err:
            resp = SQCResponse.err(str(err))
        except InternalError as err:
            resp = SQCResponse.err("An internal error occured")
        finally:
            self.repo.delete_request(request)
            if resp:
                self.repo.write_response(request, resp)

    def run(self, *args, **kwargs) -> None:
        while not self.should_stop:
            try:
                super().run(*args, **kwargs)
            except Exception as err:
                logger.exception(err)

        self.connection.release()
