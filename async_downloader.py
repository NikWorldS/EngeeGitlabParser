import os
from os import mkdir
from os.path import exists

import aiohttp
import asyncio


class Downloader:
    def __init__(self):
        if not exists("caught_files.txt"):
            print("'caught_files.txt' file not found.")
            exit()

        if not exists("models"):
            mkdir("models/")

        with open("caught_files.txt", "r", encoding="utf-8") as f:
            self.__caught_projects = f.readlines()

    @staticmethod
    async def download_project(session: aiohttp.ClientSession, url: str) -> bool:
        async with (session.get(url) as response):
            if response.status == 200:
                data = await response.content.read()
                file_name = url.strip().split('/')[-1]
                model_path = "models/" + file_name
                with open(model_path, 'wb') as f:
                    f.write(data)
                    return True
            return False


    async def main(self):
        async with aiohttp.ClientSession() as session:
            tasks = [self.download_project(session, url) for url in self.__caught_projects]
            result = await asyncio.gather(*tasks)
            print(f"TOTAL FILES: {len(result)}")
            print(f"PROBLEM FILES: {result.count(False)}")


if __name__ == '__main__':
    downloader = Downloader()

    asyncio.run(downloader.main())
