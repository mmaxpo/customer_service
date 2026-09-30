FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml .

RUN pip install -U pip \
 && pip install .

COPY app app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]