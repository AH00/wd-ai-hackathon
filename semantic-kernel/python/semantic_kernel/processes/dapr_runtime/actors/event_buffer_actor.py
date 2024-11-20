# Copyright (c) Microsoft. All rights reserved.

import json
import logging
from queue import Queue

from dapr.actor import Actor

from semantic_kernel.processes.dapr_runtime.actors.actor_state_key import ActorStateKeys
from semantic_kernel.processes.dapr_runtime.interfaces.message_buffer_interface import MessageBufferInterface
from semantic_kernel.utils.experimental_decorator import experimental_class

logger = logging.getLogger(__name__)


@experimental_class
class EventBufferActor(Actor, MessageBufferInterface):
    """Represents a message buffer actor that manages a queue of JSON strings representing events."""

    queue: Queue = Queue()

    async def enqueue(self, message: str) -> None:
        """Enqueues a JSON string message event into the buffer and updates the state.

        Args:
            message: The message event to enqueue as a JSON string.

        Raises:
            Exception: If an error occurs during the enqueue operation.
        """
        try:
            self.queue.put(message)

            queue_list = list(self.queue.queue)
            queue_json = json.dumps(queue_list)

            await self._state_manager.try_add_state(ActorStateKeys.EventQueueState.value, queue_json)
            await self._state_manager.save_state()
            logger.info(f"Enqueued message and updated state for actor ID: {self.id.id}")
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error in enqueue: {error_message}")
            raise Exception(error_message)

    async def dequeue_all(self) -> list[str]:
        """Dequeues all process events from the buffer and returns them as JSON strings.

        Returns:
            A list of JSON strings representing the dequeued messages.

        Raises:
            Exception: If an error occurs during the dequeue operation.
        """
        try:
            items = []

            while not self.queue.empty():
                items.append(self.queue.get())

            await self._state_manager.try_add_state(ActorStateKeys.EventQueueState.value, json.dumps([]))
            await self._state_manager.save_state()
            logger.info(f"Dequeued all messages and updated state for actor ID: {self.id.id}")

            return items
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error in dequeue_all: {error_message}")
            raise Exception(error_message)

    async def _on_activate(self) -> None:
        """Activates the actor and initializes the queue state from Dapr storage.

        Raises:
            Exception: If an error occurs during actor activation.
        """
        try:
            logger.info(f"Activating actor with ID: {self.id.id}")

            state_exists, queue_json = await self._state_manager.try_get_state(ActorStateKeys.EventQueueState.value)
            if state_exists and queue_json:
                queue_list = json.loads(queue_json)
                self.queue = Queue()
                for item in queue_list:
                    self.queue.put(item)
                logger.info(f"Reconstructed queue from state for actor ID: {self.id.id}")
            else:
                self.queue = Queue()
                logger.info(f"No existing state found. Initialized empty queue for actor ID: {self.id.id}")
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error in _on_activate: {error_message}")
            raise Exception(error_message)
