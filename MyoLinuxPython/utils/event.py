"""
Copyright 2022 Phuc Thanh-Thien Nguyen
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# Event-driven programming for IMU data logging
# Reference:
# https://emptypage.jp/notes/pyevent.en.html
# https://github.com/sebastiankmiec/PythonMyoLinux/pymyolinux

from typing import Optional, TypeVar, Callable, Any, Type

__all__ = [
    'Event',
    'EventHandler',
    'EventType',
    'EventHandlerType',
]


EventType = TypeVar('EventType', bound='Event')
EventHandlerType = TypeVar('EventHandlerType', bound='EventHandler')


class Event:
    is_pass_sender = False

    def __init__(self, doc: Optional[str] = None, is_fire: bool = False):
        """

        :param doc: documentation.
        :param is_fire: whether to pass sender object or not. Default: False.
        """

        self.__doc__ = doc
        self.is_fire = is_fire

    def __get__(self, obj: Optional[EventType], objtype: Optional[Type[object]] = None):
        if obj is None:
            return self
        return EventHandler(self, obj)

    def __set__(self, obj: EventType, value: float):
        pass


class EventHandler:

    def __init__(self, evt: EventType, obj: EventType):
        self.evt = evt
        self.obj = obj

    def _get_func_list(self):
        try:
            event_handler = self.obj.__eventhandler__
        except AttributeError:
            event_handler = self.obj.__eventhandler__ = {}
        return event_handler.setdefault(self.evt, [])

    def add(self, func: Callable[..., Any]):
        """
        Add new event handler function.
        Event handler function must be defined as func(sender, arg)).
        You can add handler also by using `+=` operator.

        :param func: event handler function
        :return:
        """

        self._get_func_list().append(func)
        # return a reference to the instance object on which it is called
        return self

    def remove(self, func: Callable[..., Any]):
        """
        Remove existing event handler function.
        You can remove handler also by using `-=` operator.

        :param func: the event handler function.
        :return:
        """
        self._get_func_list().remove(func)
        return self

    def fire(self, **kwargs):
        """
        Fire the event and call all event handler functions.
        You can call EventHandler object itself like a(arg) instead of a.fire(arg).

        :param kwargs: the argument dictionary.
        :return:
        """

        # keep track of event count
        try:
            event_counter = self.obj.__eventcounter__
        except AttributeError:
            event_counter = self.obj.__eventcounter__ = {}

        if self.evt in event_counter:
            event_counter[self.evt] += 1
        else:
            event_counter[self.evt] = 1

        for func in self._get_func_list():
            if self.evt.is_fire == self.evt.is_pass_sender:
                func(self.obj, **kwargs)
            else:
                func(**kwargs)

    __iadd__ = add
    __isub__ = remove
    __call__ = fire
