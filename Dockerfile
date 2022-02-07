FROM alpine:3.15 as builder

# This hack is widely applied to avoid python printing issues in docker containers.
# See: https://github.com/Docker-Hub-frolvlad/docker-alpine-python3/pull/13
ENV PYTHONUNBUFFERED=1

RUN echo "**** Update our alpine image ****" && \
    apk --no-cache update && apk upgrade &&\
    \
    echo "**** install Python ****" && \
    apk add --no-cache python3 make && \
    if [ ! -e /usr/bin/python ]; then ln -sf python3 /usr/bin/python ; fi && \
    \
    echo "**** install pip ****" && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --no-cache --upgrade pip && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi

#    pip3 install --no-cache --upgrade pip setuptools wheel && \

RUN adduser -Dh /app  appuser
WORKDIR /app

ADD requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

ADD . /app
RUN chown -R appuser /app
USER appuser

FROM builder as container-unit-test
ENTRYPOINT ["sh", "runContainerTest.sh"]

FROM builder
CMD ["--showconfig"]
ENTRYPOINT ["python3", "/app/dwsutil.py"]
