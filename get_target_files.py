import time
import requests

links_arr: list[str] = []

start = time.perf_counter()

with open("links_to_files.txt", mode="r", encoding="utf-8") as input_f:
    row = input_f.readline()


    while row:
        links_arr.append(row.strip())
        row = input_f.readline()


target_f = open("target_projects.txt", mode="w", encoding="UTF-8")
error_links: list[str] = []
targeted_links_counter: int = 0
for link in links_arr:
    r = requests.get(link)
    code = r.text
    if "<!DOCTYPE html>" in code:
        error_links.append(link)
    elif "add_block" in code:
        target_f.write(link + "\n")
        targeted_links_counter += 1

target_f.close()
stop = time.perf_counter()

print(f"COUNT OF LINKS: {len(links_arr)}")
print(f"TARGETED LINKS COUNT: {targeted_links_counter}")
print(f"LINKS WITH ERRORS: {len(error_links)}")
print(f"ERROR LINKS: {error_links}")
print(f"NOT A TARGET LINKS: {len(links_arr) - targeted_links_counter - len(error_links)}")
print(f"USED TIME: {stop - start}")