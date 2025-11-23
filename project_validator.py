from time import perf_counter

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import os

from selenium.webdriver.support.wait import WebDriverWait

from get_project_links import login, is_login_page

if __name__ == "__main__":
    start = time.perf_counter()

    links: list[str] = []
    with open("links.txt", mode='r', encoding="UTF-8") as links_file:
        row = links_file.readline()
        while row:
            links.append(row.strip())
            row = links_file.readline()

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    driver.get("https://git.engee.com")

    if is_login_page(driver):
        login(driver)

    file_links: list[str] = []

    with open("links_to_files.txt", mode="w", encoding="UTF-8") as output_f:

        for link in links:
            driver.get(link)

            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
            )

            rows = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tbody tr.tree-item"))
            )

            for row in rows:
                file = row.find_element(By.TAG_NAME, "a")
                file_name = file.get_attribute("title")

                if re.search(r"\b[\w\-\.]+\.ngscript$", file_name):
                    # file_links.append(f"{link}-/raw/master/{file_name}")
                    output_f.write(f"{link}/-/raw/master/{file_name}\n")

    stop = time.perf_counter()

    print(f"USED TIME: {stop - start}")

