from typing import Optional, Callable
from os.path import exists

import aiohttp
import asyncio


class Downloader:
    def __init__(
        self,
        work_dir: str = ".",
        max_concurrent_requests: int = 50
    ) -> None:
        self.__work_dir: str = work_dir
        if not exists(self.__work_dir):
            raise FileNotFoundError(f"Work dir `{self.__work_dir}` does not exist")
        self.__max_concurrent_requests: int = max_concurrent_requests

        self._on_progress: Optional[Callable[[int, float], None]] = None
        self.__semaphore: Optional[asyncio.Semaphore] = None

        self.__file_links: Optional[list[str]] = None

    def set_on_progress(self, on_progress: Callable[[int, float], None]):
        """
        Устанавливает значение поля `_on_progress`, хранит функцию обновления прогресса
        :param on_progress: функция обновления прогресса
        """
        self._on_progress = on_progress

    def set_file_links(self, file_links: list[str]) -> None:
        """
        :param file_links: лист со ссылками для скачивания моделей
        """
        self.__file_links = file_links

    def get_links_count(self) -> int:
        """
        :return: Возвращает количество полученных ссылок на файлы.
        """
        return len(self.__file_links)

    async def _emit_progress(self, advance: int = 1) -> None:
        """
        Вызывает функцию продвижения прогресса для прогресс-бара (если поле заполнено).
        :param advance: Значение продвижения (законченных задач)
        """
        if self._on_progress is None:
            return

        result = self._on_progress(advance)
        if asyncio.iscoroutine(result):
            await result

    async def __get_response(self, session: aiohttp.ClientSession, url: str) -> bytes:
        """
        Возвращает байты файла для сохранения модели
        :param session: Сессия aiohttp клиента
        :param url: ссылка для отправки запроса
        :return: файл в байтовом представлении
        """
        if self.__semaphore is None:
            raise Exception('Semaphore not initialized')

        async with self.__semaphore:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.content.read()
                return None

    async def download_project(self, session: aiohttp.ClientSession, url: str) -> bool:
        """
        Скачивает файл модели и сохраняет в рабочей папке текущего run'a.
        :param session: Сессия aiohttp клиента
        :param url: ссылка для отправки запроса
        :return: True, если файл сохранён; False, иначе
        """
        data = await self.__get_response(session, url)
        if data is None:
            return False

        file_name = url.split('/')[-1]
        file_path = self.__work_dir + '/models' + "/" + file_name
        with open(file_path, 'wb') as f:
            f.write(data)
            return True

    async def main(self):
        """
        Точка входа в установщик. Создаёт клиент, раздаёт задачи и принимает их, вызывая продвижение прогресса.
        :return:
        """
        if self.__file_links is None:
            raise Exception("Gets 0 links for downloading.")

        aio_connector = aiohttp.TCPConnector(limit=self.__max_concurrent_requests)
        self.__semaphore = asyncio.Semaphore(self.__max_concurrent_requests)
        async with aiohttp.ClientSession(connector=aio_connector) as session:
            tasks = [
                self.download_project(session, url)
                for url in self.__file_links
            ]

            for task in asyncio.as_completed(tasks):
                await task
                await self._emit_progress(1)



if __name__ == '__main__':
    downloader = Downloader()

    asyncio.run(downloader.main())
