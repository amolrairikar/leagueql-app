# Build context is ./src so the shared ``common`` package can be vendored
# alongside the handler, exactly as build_lambda_zip.sh does for the Lambdas.
#
#   docker build -f src/sleeper_player_stats_refresher/Dockerfile ./src
FROM python:3.13-slim

WORKDIR /app

# Dependencies first for layer caching.
COPY sleeper_player_stats_refresher/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Handler + its utils re-export live at /app so ``from utils import ...`` resolves;
# the shared common package lands at /app/common so ``from common.http import ...``
# resolves — mirroring how the zip vendors both.
COPY sleeper_player_stats_refresher/handler.py ./handler.py
COPY sleeper_player_stats_refresher/utils.py ./utils.py
COPY common ./common

CMD ["python", "handler.py"]
