# TODO: type annotation
class Event:
    """
    Event management class
    """
    def __init__(self):
        self.event_listeners = []

    def add_listener(self, listener):
        self.event_listeners.append(listener)

    def notify(self, event):
        for listener in self.event_listeners:
            listener(event)
