import sys
from enum import Enum

import aiohttp
import asyncio
import requests

from Deque import Deque

class WorkType(Enum):
    CHECK_PROJECTS = "CHECK_PROJECTS"
    CATCH_FILES = "CATCH_FILES"

class Parser:
    def __init__(self, work_type: WorkType):
        self.work_type: WorkType = work_type
        self.__projects_WEF: list[str] = []
        self.__last_project_id = requests.get("https://git.engee.com/api/v4/projects?per_page=1&order_by=id&sort=desc").json()[0].get("id")

        if self.work_type == WorkType.CHECK_PROJECTS:
            self.__file_name: str = "checked_projects.txt"
        elif self.work_type == WorkType.CATCH_FILES:
            self.__file_name: str = "caught_files.txt"

    @staticmethod
    async def catch_all_engee_models(session: aiohttp.ClientSession, project_link, project_id: int, branch: str) -> list[str]:
        base_url: str = f"https://git.engee.com/api/v4/projects/{project_id}/repository/tree"
        folders_deque: Deque = Deque()
        engee_models: list = list()

        folders_deque.add_right(" ")  # корень репозитория

        while folders_deque:
            current_path: str = folders_deque.pop_left()
            async with session.get(base_url + "?path=" + current_path) as response:
                if response.status == 200:
                    tree_data: dict = await response.json()
                    for file in tree_data:
                        if ".engee" in file.get("name"):
                            link: str = f"{project_link}/-/raw/{branch}/{file.get('path')}"
                            engee_models.append(link)
                        if file.get("type") == "tree":
                            folders_deque.add_right(file.get("path"))
        return engee_models

    @staticmethod
    async def is_engee_in_project(session: aiohttp.ClientSession, project_id: int) -> bool:
        """Ищет по директории проекта файлы формата '.engee', даже в папках внутри."""
        base_url: str = f"https://git.engee.com/api/v4/projects/{project_id}/repository/tree"
        deque: Deque = Deque()

        deque.add_right(" ")  # корень репозитория

        while deque:
            current_path: str = deque.pop_left()
            async with session.get(base_url + "?path=" + current_path) as response:
                if response.status == 200:
                    tree_data: dict = await response.json()
                    for file in tree_data:
                        if ".engee" in file.get("name"):
                            return True
                        if file.get("type") == "tree":
                            deque.add_right(file.get("path"))
        return False

    async def fetch_project(self, session: aiohttp.ClientSession, project_id: int) -> list[int] | None:
        """Делает запрос к репозиторию проекта. Если он непустой, публичный и не является проектом 'zh' или 'en' языков,
        вызывает функцию для проверки наличия или сбора ссылок на engee файлы, в зависимости от выбора при инициализации"""
        url =  f"https://git.engee.com/api/v4/projects/{project_id}"
        async with (session.get(url) as response):
            if response.status == 200:
                data = await response.json()
                if data.get("visibility") == "public":
                    name_with_namespace = data.get("name_with_namespace")
                    if (" / en / " not in name_with_namespace.lower()) and (" / zh / " not in name_with_namespace.lower()):
                        project_link = data.get("web_url")
                        current_branch = data.get("default_branch")
                        async with session.get(url + "/repository/tree") as tree_response:
                            if tree_response.status == 200:
                                if self.work_type == WorkType.CHECK_PROJECTS:
                                    engee = await self.is_engee_in_project(session, project_id)
                                    if engee:
                                        engee = [project_link]

                                elif self.work_type == WorkType.CATCH_FILES:
                                    engee = await self.catch_all_engee_models(session, project_link, project_id, current_branch)
                                return engee
            return None

    async def main(self) -> str:
        """Точка входа. Создаёт клиент для запросов и раздаёт задания, в конце записывает все полученные значения в массив."""
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_project(session, i) for i in range(self.__last_project_id)]
            results = await asyncio.gather(*tasks)
            for urls in results:
                if urls:
                    self.__projects_WEF.extend(urls)

        try:
            with open(self.__file_name, mode="w", encoding="utf-8") as output_file:
                for project_link in self.__projects_WEF:
                    output_file.write(project_link + "\n")
            return f"File '{self.__file_name}' was created"
        except Exception as e:
            return f"Exception caught: {e}"

    def get_links_count(self) -> int:
        """Возвращает количество собранных проектов."""
        return len(self.__projects_WEF)


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


