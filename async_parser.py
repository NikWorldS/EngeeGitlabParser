import aiohttp
import asyncio

import requests


class Parser:
    def __init__(self):
        self.__projects_WEF: list[str] = []
        self.__checked_projects: set[str] = set()
        self.__last_project_id = requests.get("https://git.engee.com/api/v4/projects?per_page=1&order_by=id&sort=desc").json()[0].get("id")


    async def fetch_project(self, session, project_id):
        url =  f"https://git.engee.com/api/v4/projects/{project_id}"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("visibility") == "public":
                    name_with_namespace = data.get("name_with_namespace")
                    if (" / en / " not in name_with_namespace) and (" / zh / " not in name_with_namespace):
                        project_link = data.get("web_url")
                        async with session.get(url + "/repository/tree") as tree_response:
                            if tree_response.status == 200:
                                tree_data = await tree_response.json()
                                if tree_data and ".engee" in tree_data[0].get("name"):
                                    return project_id, project_link

    async def main(self):
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_project(session, i) for i in range(self.__last_project_id)]
            results = await asyncio.gather(*tasks)
            self.__projects_WEF = [(url[0], url[1]) for url in results if url]

    def get_projects_WEF(self):
        with open("project_links.txt", mode="w", encoding="utf-8") as output_file:
            for id, link in self.__projects_WEF:
                output_file.write(str(id) + " | " + link + "\n")

    def get_links_count(self):
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