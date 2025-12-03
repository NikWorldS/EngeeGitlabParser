import aiohttp
import asyncio
import requests

from Deque import Deque


class Parser:
    #TODO: remove __examples, __reg_examples, __checked_projects
    def __init__(self):
        self.__projects_WEF: list[str] = []
        self.__checked_projects: set[str] = set()  # staying here for tests
        self.__examples: dict[str: int] = dict()  # staying here for tests
        self.__reg_examples: dict[str: int] = {'ru': 0, "zh": 0, "en": 0}  # staying here for tests
        self.__last_project_id = requests.get("https://git.engee.com/api/v4/projects?per_page=1&order_by=id&sort=desc").json()[0].get("id")



    #TODO: возможно, новая функция для сбора ссылок на файлы .engee
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

    async def fetch_project(self, session: aiohttp.ClientSession, project_id: int) -> tuple[int, str]:
        """Делает запрос к репозиторию проекта. Если он непустой, публичный и не является проектом 'zh' или 'en' языков,
        вызывает функцию для проверки наличия файла '.engee'."""
        url =  f"https://git.engee.com/api/v4/projects/{project_id}"
        async with (session.get(url) as response):
            if response.status == 200:
                data = await response.json()
                if data.get("visibility") == "public":
                    name_with_namespace = data.get("name_with_namespace")
                    # if " / examples / " in name_with_namespace.lower():
                    #     if " / zh / " in name_with_namespace.lower():
                    #         self.__reg_examples["zh"] += 1
                    #     elif " / en / " in name_with_namespace.lower():
                    #         self.__reg_examples["en"] += 1
                    #     else:
                    #         self.__reg_examples["ru"] += 1
                    #     self.__checked_projects.add(name_with_namespace)
                    #     name = data.get("name")
                    #     if name in self.__examples:
                    #         self.__examples[name] += 1
                    #     else:
                    #         self.__examples[name] = 1
                    if (" / en / " not in name_with_namespace.lower()) and (" / zh / " not in name_with_namespace.lower()):

                        project_link = data.get("web_url")
                        async with session.get(url + "/repository/tree") as tree_response:
                            if tree_response.status == 200:
                                engee = await self.is_engee_in_project(session, project_id)
                                if engee:
                                    return project_id, project_link



    async def main(self) -> None:
        """Создаёт клиент для запросов и раздаёт задания, в конце записывать все полученные значения в массив"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_project(session, i) for i in range(self.__last_project_id)]
            results = await asyncio.gather(*tasks)
            self.__projects_WEF = [(url[0], url[1]) for url in results if url]

    def get_projects_WEF(self) -> str:
        """Значения из массива (заполненного в функции main) записывает в файл 'project_links.py'."""
        try:
            with open("project_links.txt", mode="w", encoding="utf-8") as output_file:
                for project_id, project_link in self.__projects_WEF:
                    output_file.write(str(project_id) + " | " + project_link + "\n")
            return "'project_links.txt' was created"
        except Exception as e:
            return f"Exception caught: {e}"

    def get_links_count(self) -> int:
        """Возвращает количество собранных проектов."""
        return len(self.__projects_WEF)


if __name__ == "__main__":
    import time
    parser = Parser()

    start = time.perf_counter()

    asyncio.run(parser.main())

    end = time.perf_counter()
    print(parser.get_links_count())
    print(parser.get_projects_WEF())
    print(f"Time elapsed: {end - start:.2f} seconds")


