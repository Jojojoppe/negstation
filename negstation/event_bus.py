import threading
import queue
import logging
import inspect
import types


class EventBus:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.subscribers = {}
        self.event_queue = queue.Queue()
        self.main_queue = queue.Queue()
        threading.Thread(target=self._dispatch_loop, daemon=True).start()

    def subscribe(self, event_type: str, callback: callable, main_thread: bool = False):
        self.logger.debug(f"Subscribed to {event_type}")
        self.subscribers.setdefault(event_type, []).append((callback, main_thread))

    def publish_deferred(self, event_type: str, data=None):
        self.logger.debug(f"publish {event_type}")
        self.event_queue.put((event_type, data))

    def _dispatch_loop(self):
        while True:
            event_type, data = self.event_queue.get()
            self.logger.debug(f"Dispatching {event_type}")
            for callback, main_thread in self.subscribers.get(event_type, []):
                if main_thread:
                    self.main_queue.put((callback, data))
                else:
                    try:
                        callback(data)
                    except Exception as e:
                        self.logger.error(
                            f"Error in background handler '{
                                     event_type}': {e}"
                        )

    def process_main_queue(self):
        while True:
            try:
                callback, data = self.main_queue.get_nowait()
                callback(data)
            except queue.Empty:
                break

    def unsubscribe_instance(self, instance):
        for event_type, subs in list(self.subscribers.items()):
            new_subs = []
            for callback, main_thread in subs:
                # if it's a bound method to our instance, skip it
                if inspect.ismethod(callback) and callback.__self__ is instance:
                    continue
                new_subs.append((callback, main_thread))
            if len(new_subs) != len(subs):
                self.subscribers[event_type] = new_subs