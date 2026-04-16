from enum import Enum

import aiohttp
import asyncio
import requests

from typing import Optional

from collections import deque

class WorkType(Enum):
    CHECK_PROJECTS = "CHECK_PROJECTS"
    CATCH_FILES = "CATCH_FILES"

class Parser:
    def __init__(self, work_type: WorkType, max_concurrent_requests: int = 50) -> None:
        """
        :param work_type: Режим работы
        :param max_concurrent_requests: максимальное количество одновременных запросов
        """
        self.work_type: WorkType = work_type
        self.__max_concurrent_requests = max_concurrent_requests

        self.__semaphore: Optional[asyncio.Semaphore] = None
        self.__aio_connector: Optional[aiohttp.TCPConnector] = None

        self.__parsed_projects: list[str] = []

        if self.work_type == WorkType.CHECK_PROJECTS:
            self.__file_name: str = "../checked_projects.txt"
        elif self.work_type == WorkType.CATCH_FILES:
            self.__file_name: str = "../caught_files.txt"

    def get_last_project_id(self) -> int:
        """
        Возвращает id последнего проекта на Engee gitlab.
        :return: id последнего проекта"""
        return requests.get("https://git.engee.com/api/v4/projects?per_page=1&order_by=id&sort=desc").json()[0].get("id")

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

    async def catch_all_engee_models(
        self,
        session: aiohttp.ClientSession,
        project_link: str,
        project_id: int,
        branch: str
    ) -> list[str]:
        """
        Возвращает ссылки на все модели проекта, в которых есть файлы `.engee` формата.
        :param session: Сессия aiohttp клиента
        :param project_link: ссылка на проверяемый проект
        :param project_id:  id проверяемого проекта
        :param branch: название ветки репозитория
        :return: лист со ссылками на файлы для скачивания.
        """
        base_url: str = f"https://git.engee.com/api/v4/projects/{project_id}/repository/tree"
        folders_deque: deque[str] = deque()
        engee_models: list = list()

        folders_deque.appendleft("")  # корень проверяемого проекта

        while folders_deque:
            current_path: str = folders_deque.popleft()
            url: str = f"{base_url}?path={current_path}"
            tree_data: dict = await self.__get_response(session, url)

            if not tree_data:
                continue

            for file in tree_data:
                if ".engee" in file.get("name"):
                    link: str = f"{project_link}/-/raw/{branch}/{file.get('path')}"
                    engee_models.append(link)
                if file.get("type") == "tree":
                    folders_deque.append(file.get("path"))
        return engee_models

    async def is_engee_in_project(
        self,
        session: aiohttp.ClientSession,
        project_id: int
    ) -> bool:
        """
        Возвращает True, если нашёл в директории проекта файлы формата `.engee`.
        :param session: Сессия aiohttp клиента
        :param project_id: id проверяемого проекта
        :return: bool, True (`.engee` есть в репозитории), False (иначе)
        """
        base_url: str = f"https://git.engee.com/api/v4/projects/{project_id}/repository/tree"
        project_deque: deque[str] = deque()

        project_deque.append("")  # корень проверяемого проекта

        while project_deque:
            current_path: str = project_deque.popleft()
            url: str = f"{base_url}?path={current_path}"
            tree_data: dict = await self.__get_response(session, url)

            if not tree_data:
                continue

            for file in tree_data:
                if ".engee" in file.get("name"):
                    return True
                if file.get("type") == "tree":
                    project_deque.append(file.get("path"))
        return False

    async def fetch_project(
        self,
        session: aiohttp.ClientSession,
        project_id: int
    ) -> Optional[list[int]]:
        """
        Возвращает ссылку на проект/ссылки на скачивание моделей (файлов `.engee`), если он: непустой, публичный,
        исходный пример (исключает примеры на zh-китайском и en-английском языках) в зависимости от выбора.
        :param session: Сессия aiohttp клиента
        :param project_id: id проверяемого проекта
        :return: лист ссылок на проект/файлы
        """
        url: str = f"https://git.engee.com/api/v4/projects/{project_id}"
        data: dict = await self.__get_response(session, url)

        if not data:
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

        if self.work_type == WorkType.CHECK_PROJECTS:
            has_engee_f = await self.is_engee_in_project(session, project_id)
            if has_engee_f:
                return [project_link]

        elif self.work_type == WorkType.CATCH_FILES:
            return await self.catch_all_engee_models(session, project_link, project_id, current_branch)

        return None

    async def main(self) -> bool:
        """
        Точка входа. Создаёт клиент для запросов и раздаёт задания, записывая результаты задач асинхронно.
        :return: True, если ошибок не возникло; False, иначе
        """
        aio_connector = aiohttp.TCPConnector(limit=self.__max_concurrent_requests)
        self.__semaphore = asyncio.Semaphore(self.__max_concurrent_requests)
        async with aiohttp.ClientSession(connector=aio_connector) as session:
            tasks = [
                asyncio.create_task(self.fetch_project(session, project_id))
                for project_id in range(0, self.get_last_project_id() + 1)
            ]

            with open(self.__file_name, mode="w", encoding="utf-8") as output_file:
                for task in asyncio.as_completed(tasks):
                    urls = await task
                    if not urls:
                        continue

                    self.__parsed_projects.extend(urls)
                    for url in urls:
                        output_file.write(f"{url}\n")
                    output_file.flush()
        return True

    def get_links_count(self) -> int:
        """Возвращает количество собранных проектов."""
        return len(self.__parsed_projects)


if __name__ == "__main__":
    import time
    user_input: str = input("Choose type of work for parser (enter a number):\n1. CHECK PROJECTS - for catching link to PROJECTS\n2. CATCH FILES - for catching links to FILES\n")
    if user_input == "1":
        work_type: WorkType = WorkType.CHECK_PROJECTS
    elif user_input == "2":
        work_type: WorkType = WorkType.CATCH_FILES
    else:
        print("Invalid work type")
        exit()
    print("Current work type: ", work_type)
    print("Parsing process started...\n")

    parser = Parser(work_type)

    start = time.perf_counter()

    asyncio.run(parser.main())

    end = time.perf_counter()

    print("Caught links: ", parser.get_links_count())
    print(f"Time elapsed: {end - start:.2f} seconds")
