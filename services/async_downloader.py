from typing import Optional, Callable
from os.path import exists
from os import mkdir

import aiohttp
import asyncio


class Downloader:
    def __init__(self, work_dir: str = "", max_concurrent_requests: int = 50):
        self.__semaphore: Optional[asyncio.Semaphore] = None
        self.__work_dir: str = work_dir
        if not exists(self.__work_dir):
            raise FileNotFoundError(f"Work dir `{self.__work_dir}` does not exist")
        self.__max_concurrent_requests: int = max_concurrent_requests

        self._on_progress: Callable[[int, int], None] = None

        self.__file_links: Optional[list[str]] = None

    def set_on_progress(self, on_progress: Callable[[int], None]):
        self.__on_progress = on_progress
    def set_file_links(self, file_links: list[str]):
        self.__file_links = file_links

    def get_links_count(self) -> int:
        return len(self.__file_links)

    async def _emit_progress(self, advance: int = 1) -> None:
        if self._on_progress is None:
            return

        result = self._on_progress(advance)
        if asyncio.iscoroutine(result):
            await result

    async def __get_response(self, session: aiohttp.ClientSession, url: str):
        if self.__semaphore is None:
            raise Exception('Semaphore not initialized')

        async with self.__semaphore:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.content.read()
                return None

    async def download_project(self, session: aiohttp.ClientSession, url: str) -> bool:
        data = await self.__get_response(session, url)
        if data is None:
            return False

        file_name = url.split('/')[-1]
        file_path = self.__work_dir + '/' + file_name
        with open(file_path, 'wb') as f:
            f.write(data)
            return True

    async def main(self):
        aio_connector = aiohttp.TCPConnector(limit=self.__max_concurrent_requests)
        self.__semaphore = asyncio.Semaphore(self.__max_concurrent_requests)
        async with aiohttp.ClientSession(connector=aio_connector) as session:
            tasks = [
                self.download_project(session, url)
                for url in self.__file_links
            ]

            for _ in asyncio.as_completed(tasks):
                await self._emit_progress(1)



if __name__ == '__main__':
    downloader = Downloader()

    asyncio.run(downloader.main())
