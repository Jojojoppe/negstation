import logging
from collections import defaultdict

class GlobalState:
    def __init__(self):
        self.listeners = defaultdict(list)

        self.raw_params = {
            "use_auto_wb": False,
            "use_camera_wb": True,
            "no_auto_bright": True,
            "output_bps": 16,
            "gamma": (2.222, 4.5), # Default sRGB gamma
        }
        self.raw_image_data = None

    def subscribe(self, event_name: str, callback):
        """Register a function to be called when an event is dispatched."""
        logging.info(f"Subscribing '{callback.__qualname__}' to event '{event_name}'")
        self.listeners[event_name].append(callback)

    def dispatch(self, event_name: str, *args, **kwargs):
        """Call all registered callbacks for a given event."""
        logging.debug(f"Dispatching event '{event_name}' with data: {kwargs}")
        if event_name in self.listeners:
            for callback in self.listeners[event_name]:
                try:
                    # Pass the arguments and keyword arguments to the callback
                    callback(*args, **kwargs)
                except Exception as e:
                    logging.error(f"Error in event callback for '{event_name}': {e}")