# pyfog on Debian, the same way it runs on a FOG server: python3 and the
# distro's python3-pymysql, nothing from pip.
FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pymysql \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
ENTRYPOINT ["python3", "-m", "pyfog"]
