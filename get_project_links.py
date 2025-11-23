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


def is_login_page(driver):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        classes = body.get_attribute("class")
        return "login-page" in classes
    except NoSuchElementException:
        return False

def is_object_exists(driver: webdriver, type: str, key: str):
    try:
        body = driver.find_element(By.TAG_NAME, type)
        elements = body.get_attribute("class")
        print("elements", elements)
        return key in elements

    except NoSuchElementException:
        return False

def get_links(driver, projects_temp):
    start = time.perf_counter()
    for i in range(2, 51):
        ul = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "ul.projects-list")))
        # Находим все элементы проекта
        items = ul.find_elements(By.CLASS_NAME, "project-row")
        for item in items:
            a = item.find_element(By.TAG_NAME, "a")
            link = a.get_attribute("href")

            projects_temp.append(link)

        driver.get(f"https://git.engee.com/explore?page={i}")

    stop = perf_counter()
    print(f"USED TIME TO GET ALL LINKS: {stop - start}")

def check_files(link: str, repo_links: list[str]):
    driver.get(link)

    table = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
    )

    rows = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tbody tr.tree-item"))
    )

    is_engee_file_exists = False
    is_ngscript_file_exists = False

    for row in rows:
        file = row.find_element(By.TAG_NAME, "a")
        file_name = file.get_attribute("title")
        if re.search(r"\b[\w\-\.]+\.engee$", file_name):
            is_engee_file_exists = True
        if re.search(r"\b[\w\-\.]+\.ngscript$", file_name):
            is_ngscript_file_exists = True

        if is_ngscript_file_exists and is_engee_file_exists:
            repo_links.append(link)
            break

def login(driver: webdriver):
    try:
        login_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/div/div[2]/div[2]/div/div[3]/form/button")))
        login_button.click()

        email_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, "/html/body/div/div[2]/div/div[2]/div[1]/div[2]/div/input")))
        EMAIL = # ADD HERE YOUR EMAIL FOR LOGIN (yeah, thats unsafe, but i dont care)
        email_input.send_keys("")

        continue_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, "/html/body/div/div[2]/div/div[2]/div[1]/div[2]/div/div[2]/button")))
        continue_button.click()

        password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, "/html/body/div/div[2]/div/div[2]/div[1]/div[2]/div[2]/div[1]/input")))
        PASSWORD = # AND ADD HERE YOUR PASSWORD (and its also unsafe, i know)
        password_input.send_keys("")

        login_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, "/html/body/div/div[2]/div/div[2]/div[1]/div[2]/div[2]/div[1]/div[2]/div/button")))
        login_button.click()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, "/html/body/div[3]/div[2]/div[4]/main/div[2]/h1")))
        driver.get("https://git.engee.com/explore")
    except Exception as e:
        driver.close()
        return (False, e)

if __name__ == "__main__":
    start_gl = time.perf_counter()

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    driver.get("https://git.engee.com")

    if is_login_page(driver):
        login(driver)

    repo_links = []
    projects_temp = []
    SCROLL_PAUSE = 2

    get_links(driver, projects_temp)

    start = time.perf_counter()

    for link in projects_temp:
        check_files(link, repo_links)

    stop = time.perf_counter()
    print(f"USED TIME TO CHECK ALL PROJECTS: {stop - start}")

    with open("links.txt", mode="w", encoding="UTF-8") as output:
        for link in repo_links:
            output.write(link + "\n")

    stop_gl = time.perf_counter()
    print(f"ALL TIME:{stop_gl - start_gl}")
