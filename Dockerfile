FROM python:3.12-slim AS build
ARG POETRY_VERSION=1.3.2
ENV POETRY_VENV=/opt/poetry-venv

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends --yes python3-venv gcc libpython3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    python3 -m venv "${POETRY_VENV}" \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install "poetry==${POETRY_VERSION}"

ENV PATH="${PATH}:${POETRY_VENV}/bin"
WORKDIR /app
COPY poetry.lock pyproject.toml ./
COPY src /app/src
COPY db /app/db
COPY README.md /app/README.md

RUN poetry config virtualenvs.create false
RUN poetry install

ENV PYTHONPATH=/app
ENV PATH="${POETRY_VENV}/bin:${PATH}"

CMD ["python", "-m", "flows.translate_meetings"]
