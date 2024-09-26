# set image base
FROM ubuntu:jammy

# set environment
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul

# Set working directory
WORKDIR /opt

# Default update
RUN apt update && apt upgrade -y

# Install R-base and rstudio
RUN apt install -y \
	r-base \
	gdebi-core \
	wget

RUN wget https://download2.rstudio.org/server/jammy/amd64/rstudio-server-2024.09.0-375-amd64.deb && \
	gdebi --non-interactive rstudio-server-2024.09.0-375-amd64.deb && \
	rm rstudio-server-2024.09.0-375-amd64.deb

# Expose port 8080 for RStudio Server
EXPOSE 8787

# Default entrypoint to start RStudio Server
ENTRYPOINT ["/bin/bash"]


