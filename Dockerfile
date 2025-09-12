FROM python:3.11-slim
RUN mkdir /code
COPY requirements.txt /code
WORKDIR /code

RUN apt update && apt install -y glpk-utils

RUN pip install -r requirements.txt

COPY ./forest_ensys /code/forest_ensys

ENV PYTHONUNBUFFERED=TRUE
EXPOSE 9000
CMD ["uvicorn", "forest_ensys.app:app", "--host", "0.0.0.0", "--port", "9000", "--log-level", "debug"]