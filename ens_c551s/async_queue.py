from __future__ import annotations
import asyncio
import collections
import threading
import typing


class async_queue:
    __backlog: collections.deque[typing.Coroutine[typing.Any, typing.Any, None]]
    __closed: bool
    __event: asyncio.Event
    __lock: threading.Lock
    __loop: asyncio.AbstractEventLoop
    __task: asyncio.Task[None]

    def __init__(self: async_queue) -> None:
        self.__backlog = collections.deque()
        self.__closed = False
        self.__event = asyncio.Event()
        self.__lock = threading.Lock()
        self.__loop = asyncio.get_running_loop()
        self.__task = self.__loop.create_task(self.__run())

    async def close(self: async_queue) -> None:
        with self.__lock:
            self.__closed = True
            self.__event.set()
        await self.__task

    def queue(
        self: async_queue, coroutine: typing.Coroutine[typing.Any, typing.Any, None]
    ) -> None:
        self.__loop.call_soon_threadsafe(self.__queue, coroutine)

    def __queue(
        self: async_queue, coroutine: typing.Coroutine[typing.Any, typing.Any, None]
    ) -> None:
        with self.__lock:
            self.__backlog.append(coroutine)
            self.__event.set()

    async def __run(self: async_queue) -> None:
        while True:
            await self.__event.wait()
            with self.__lock:
                if len(self.__backlog) > 0:
                    coroutine = self.__backlog.popleft()
                elif self.__closed:
                    break
                else:
                    self.__event.clear()
                    continue
            await coroutine
