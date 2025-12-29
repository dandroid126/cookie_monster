FROM ghcr.io/astral-sh/uv:python3.13-alpine

ENV TZ="US/Pacific" UV_SYSTEM_PYTHON=1
WORKDIR /app
RUN adduser -D python
RUN install -d -m 700 -o python -g python out
RUN apk update && apk add --no-cache --update git apk-cron libcap
RUN chown python:python /bin/busybox && setcap cap_setgid=ep /bin/busybox
COPY requirements.txt requirements.txt
RUN uv pip install --no-cache-dir -r requirements.txt
COPY src src
COPY cron/cookie_monster.cron /var/spool/cron/crontabs/python

# Uncomment the line below to copy the test cron file. This runs the job every 1 minute instead of once a week
# COPY cron/cookie_monster_test.cron /var/spool/cron/crontabs/python

# Switch to python user and set the CMD
USER python
ENV PYTHONPATH='/app'
CMD /usr/sbin/crond -l 8 -L /app/out/cron.log && python3 src/client.py

# Uncomment the line below to hold open a container failing to start for debugging purposes
# CMD [ "sleep", "infinity" ]
