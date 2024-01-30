# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/engine/reference/builder/

ARG PYTHON_VERSION=3.10.9
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#user
ARG UID=10001
#RUN adduser \
#    --disabled-password \
#    --gecos "" \
#    --home "/nonexistent" \
#    --shell "/sbin/nologin" \
#    --no-create-home \
#    --uid "${UID}" \
#    appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

RUN apt update
RUN apt-get -y install bc
RUN apt -y install vim
RUN apt -y install pandoc
RUN apt -y install imagemagick
RUN apt -y install texlive-latex-base
RUN apt-get -y install texlive-xetex texlive-fonts-recommended texlive-lang-cyrillic

#RUN cp /etc/ImageMagick-6/policy.xml /app/policy.xml
# Copy the source code into the container.
COPY . .

RUN cat /app/policy.xml > /etc/ImageMagick-6/policy.xml
RUN chmod 755 /app/fmin_data_production
RUN pip install python-telegram-bot[job-queue] --pre

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
CMD python3 main.py -t="FMIN_TOKEN" -p="fmin_data_production"
