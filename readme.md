# new specs!!!
now previous version in "Archived" directory (not all of them is working, but I saved it by the way)

# Current version
Now there little async parser to catching project from Engee gitlab that have ".engee" files in repo by GitLab API.
For run it, just need to start "async_parser.py" without any changes. Result file - "projects_links.txt".

# Previois (archived) version
## This is lite parser for catching some projects from engee gitlab.

# Steps for work with previos version
1. Add email and password (i did this with logining) into login function (get_project_links.py)
2. Run get_project_links.py. This file creates "links.txt" with links to projects, thats contains each of .ngscript and .engee files 
3. Next step - run "project_validator.py". Its creates new "links_to_file.txt" with links to .ngscript files (in raw format)
4. Run "get_target_files.py". It will catch all files, where contains "add_block" method. Thats main property to catch projects with Public Model Control methods
5. In "target_projects.txt" will be links to raw-format files from projects.