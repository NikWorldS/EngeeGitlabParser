import aiohttp
import asyncio
import requests

from Deque import Deque


class Parser:
    def __init__(self):
        self.__projects_WEF: list[str] = []
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
                    if (" / en / " not in name_with_namespace.lower()) and (" / zh / " not in name_with_namespace.lower()):
                        project_link = data.get("web_url")
                        async with session.get(url + "/repository/tree") as tree_response:
                            if tree_response.status == 200:
                                engee = await self.is_engee_in_project(session, project_id)
                                if engee:
                                    return project_id, project_link



    async def main(self) -> None:
        """Точка входа. Создаёт клиент для запросов и раздаёт задания, в конце записывать все полученные значения в массив."""
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
            return "File 'project_links.txt' was created"
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


