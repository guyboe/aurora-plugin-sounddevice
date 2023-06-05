import hashlib
import logging
from typing import Dict, Any

from kombu import Connection, Exchange, Queue, Consumer, Producer
from kombu.utils.compat import nested
from kombu.asynchronous import Hub

from .config import Config


class Queues:

    _connection: Connection
    _channel: Any
    _producer: Producer

    _exchanges: Dict[str, Exchange] = {}
    _proxies: Dict[str, Exchange] = {}
    _proxy_queues: Dict[str, Queue] = {}

    def __init__(self):
        self._connection = Connection(self.config.queues.url)
        self._channel = self._connection.channel()
        self._producer = Producer(self._channel)
        for k, v in self.config.queues.exchanges.items():
            self._exchanges[k] = Exchange(
                v.name, type=v.type, durable=v.durable)(self._channel
            )
            self._exchanges[k].declare()

            self._proxies[k] = Exchange(
                v.proxy, type=v.type, durable=v.durable)(self._channel
            )
            self._proxies[k].declare()

            self._proxy_queues[k] = Queue(
                v.proxy,
                self._proxies[k],
                routing_key="*",
                durable=v.durable,
                queue_arguments={ "x-dead-letter-exchange": v.name }
            )(self._channel)
            self._proxy_queues[k].declare()

    def consume(self):

        hub = Hub()

        self._connection.register_with_event_loop(hub)

        consumers = []

        def get_queue(queue: Config.Queues.Queue, exchange: str):
            consumer_arguments = {}
            match self._connection.transport.driver_type:
                case "amqp":
                    if queue.priority:
                        consumer_arguments["x-priority"] = queue.priority
            result = Queue(
                queue.name,
                exchange=self._exchanges[exchange],
                channel=self._channel,
                routing_key=queue.routing_key,
                durable=queue.durable,
                exclusive=queue.exclusive,
                auto_delete=queue.auto_delete,
                consumer_arguments=consumer_arguments
            )
            result.declare()
            return result

        for queue in self.config.queues.queues:
            consumers.append(Consumer(self._channel, get_queue(queue, queue.exchange), accept=["pickle"]))
            consumers[-1].register_callback(getattr(self, queue.callback))
            logging.info(
                "Ready for consuming data from %s with plugin %s", queue.name, self.NAME
            )

        with nested(*consumers):
            hub.run_forever()

    def publish(
        self,
        body: bytes,
        *,
        exchange: str,
        routing_key: str = "*",
        source: str = None,
        expiration: int = 0,
    ) -> Dict[str, Any]:
        hash_ = hashlib.sha256(body).hexdigest()
        self._producer.publish(
            body,
            exchange=self._proxies[exchange],
            routing_key=routing_key,
            headers={ "v-source": source, "v-hash": hash_ },
            expiration=expiration,
        )
        return { "hash": hash_ }
