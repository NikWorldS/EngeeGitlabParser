from typing import Optional, Callable

import aiohttp
import asyncio
import requests

from collections import deque


class Parser:
    def __init__(
            self,
            work_dir: str = "",
            max_concurrent_requests: int = 50,
    ) -> None:
        """
        :param max_concurrent_requests: максимальное количество одновременных запросов
        """
        self.work_dir = work_dir
        self.__max_concurrent_requests = max_concurrent_requests

        self._on_progress: Optional[Callable[[int, float], None]] = None

        self.__semaphore: Optional[asyncio.Semaphore] = None
        self.__aio_connector: Optional[aiohttp.TCPConnector] = None

        self.__parsed_links: list[str] = []
    @staticmethod
    def get_last_project_id() -> int:
        """
        Возвращает id последнего проекта на Engee gitlab.
        :return: id последнего проекта"""
        return requests.get("https://git.engee.com/api/v4/projects?per_page=1&order_by=id&sort=desc").json()[0].get("id")

    def set_on_progress(self, on_progress: Callable) -> None:
        """
        Устанавливает значение поля `_on_progress`, хранит функцию обновления прогресса
        :param on_progress: функция обновления прогресса
        """
        self._on_progress = on_progress

    def get_links_count(self) -> int:
        """
        :return: Возвращает количество захваченных ссылок на файлы.
        """
        return len(self.__parsed_links)

    def get_project_links(self) -> list[str]:
        """
        :return: Возвращает лист с захваченными ссылками
        """
        return self.__parsed_links

    async def __get_response(self, session: aiohttp.ClientSession, url: str) -> Optional[dict]:
        """
        Возвращает json (dict) объект при успешном запросе или None иначе.
        :param session: Сессия aiohttp клиента
        :param url: ссылка для отправки запроса
        :return: json ответ
        """
        if self.__semaphore is None:
            raise Exception("Semaphore not initialized.")

        async with self.__semaphore:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None

    async def _emit_progress(self, advance: float = 1) -> None:
        """
        Вызывает функцию продвижения прогресса для прогресс-бара (если поле заполнено).
        :param advance: Значение продвижения (законченных задач)
        """
        if self._on_progress is None:
            return

        result = self._on_progress(advance)
        if asyncio.iscoroutine(result):
            await result

    async def catch_all_engee_models(
            self,
            session: aiohttp.ClientSession,
            project_link: str,
            project_id: int,
            branch: str
    ) -> tuple[str, list[str]]:
        """
        Возвращает кортеж из: ссылки на проект(репозиторий) и всех ссылок на модели `.engee` из проекта.
        :param session: Сессия aiohttp клиента
        :param project_link: ссылка на проверяемый проект
        :param project_id:  id проверяемого проекта
        :param branch: название ветки репозитория
        :return: tuple; кортеж с: ссылкой на проект, все ссылки на файлы `.engee` проекта.
        """
        base_url: str = f"https://git.engee.com/api/v4/projects/{project_id}/repository/tree"
        folders_deque: deque[str] = deque()
        engee_models: list = list()

        folders_deque.appendleft("")  # корень проверяемого проекта

        while folders_deque:
            current_path: str = folders_deque.popleft()
            url: str = f"{base_url}?path={current_path}"
            tree_data: dict = await self.__get_response(session, url)

            if tree_data is None:
                continue

            for file in tree_data:
                if ".engee" in file.get("name"):
                    link: str = f"{project_link}/-/raw/{branch}/{file.get('path')}"
                    engee_models.append(link)
                if file.get("type") == "tree":
                    folders_deque.append(file.get("path"))
        return project_link, engee_models

    async def fetch_project(
            self,
            session: aiohttp.ClientSession,
            project_id: int
    ) -> Optional[tuple[str, list[str]]]:
        """
        Возвращает ссылку на проект/ссылки на скачивание моделей (файлов `.engee`), если он: непустой, публичный,
        исходный пример (исключает примеры на zh-китайском и en-английском языках) в зависимости от выбора.
        :param session: Сессия aiohttp клиента
        :param project_id: id проверяемого проекта
        :return: лист ссылок на проект/файлы
        """
        url: str = f"https://git.engee.com/api/v4/projects/{project_id}"
        data: dict = await self.__get_response(session, url)

        if data is None:
            return None
        if data.get("visibility") != "public":
            return None

        name_with_namespace: str = data.get("name_with_namespace").lower()
        if (" / en / " in name_with_namespace) or (" / zh / " in name_with_namespace):
            return None

        project_link: str = data.get("web_url")
        current_branch: str = data.get("default_branch")
        tree_data: dict = await self.__get_response(session, url + "/repository/tree")

        if tree_data is None:
            return None

        return await self.catch_all_engee_models(session, project_link, project_id, current_branch)

    async def main(self) -> list[str]:
        """
        Точка входа. Создаёт клиент для запросов и раздаёт задания, записывая результаты задач асинхронно.
        :return: Лист захваченных ссылок
        """
        aio_connector = aiohttp.TCPConnector(limit=self.__max_concurrent_requests)
        self.__semaphore = asyncio.Semaphore(self.__max_concurrent_requests)
        async with aiohttp.ClientSession(connector=aio_connector) as session:
            tasks = [
                asyncio.create_task(self.fetch_project(session, project_id))
                for project_id in range(0, self.get_last_project_id())
            ]
            caught_projects_file = open(self.work_dir + "/caught_projects.txt", "w", encoding="utf-8")
            caught_models_file = open(self.work_dir + "/caught_models.txt", "w", encoding="utf-8")

            for task in asyncio.as_completed(tasks):
                response = await task
                if response:
                    project_link, model_links = response
                    if project_link:
                        caught_projects_file.write(project_link + "\n")
                    caught_projects_file.flush()

                    if model_links:
                        self.__parsed_links.extend(model_links)
                        for model_link in model_links:
                            caught_models_file.write(model_link + "\n")
                    caught_models_file.flush()

                await self._emit_progress(1)

        caught_projects_file.close()
        caught_models_file.close()

        return self.get_project_links()


if __name__ == "__main__":
    import time
    print("Parsing process started...\n")

    parser = Parser()

    start = time.perf_counter()

    asyncio.run(parser.main())

    end = time.perf_counter()

    print("Caught links: ", parser.get_links_count())
    print(f"Time elapsed: {end - start:.2f} seconds")
