# test


# Docker creation
docker build -t rstudio:2024-09-26 .
docker create -it --name rstudio -p 8787:8787 rstudio:2024-09-26
docker start rstudio
docker exec -it rstudio bash

# in docker...
rstudio-server start

# login id,pw
id: rstudio
pw: password

# rstudio account has sudo permission

