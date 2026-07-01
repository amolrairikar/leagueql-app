# Build context is ./src so the shared ``common`` package can be vendored alongside the
# handler, exactly as build_lambda_zip.sh does for the Lambdas.
#
#   docker build -f src/recap_generator/Dockerfile ./src
FROM python:3.13-slim

WORKDIR /app

# Dependencies first for layer caching.
COPY recap_generator/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Handler at /app so ``python handler.py`` runs; the shared common package lands at
# /app/common so ``from common.recap_llm import ...`` resolves — mirroring how the zip
# vendors both.
COPY recap_generator/handler.py ./handler.py
COPY common ./common

CMD ["python", "handler.py"]
