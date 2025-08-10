FROM docker.io/python:3.11-alpine3.18

ENV TZ="UTC"
WORKDIR /app
RUN adduser -D python
RUN install -d -m 700 -o python -g python out
RUN apk update && apk add --no-cache --update git apk-cron libcap
RUN chown python:python /bin/busybox && setcap cap_setgid=ep /bin/busybox

# This is the most time consuming part of the build. Do it as early as possible so we can cache the layers.
# This way when we change python code, we don't need to reinstall the dependencies.
COPY requirements.txt requirements.txt
USER python
ENV PYTHONPATH='/app'
RUN pip install --no-cache-dir -r requirements.txt

# Complete the setup as root
USER root
COPY src src
COPY cron/cookie_monster.cron /var/spool/cron/crontabs/python
# Uncomment the line below to copy the test cron file. This runs the job every 1 minute instead of once a week
# COPY cron/cookie_monster_test.cron /var/spool/cron/crontabs/python

# Switch back to python user and set the CMD
USER python
CMD /usr/sbin/crond -l 8 -L /app/out/cron.log && python3 src/client.py

# Uncomment the line below to hold open a container failing to start for debugging purposes
# CMD [ "sleep", "infinity" ]
