# Build context is ./src so the shared ``common`` package can be vendored alongside the
# handler, exactly as the other refresher tasks do.
#
#   docker build -f src/yahoo_player_stats_refresher/Dockerfile ./src
FROM python:3.13-slim

WORKDIR /app

# Dependencies first for layer caching.
COPY yahoo_player_stats_refresher/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Handler + its utils re-export live at /app so ``from utils import ...`` resolves; the shared
# common package lands at /app/common so ``from common.yahoo_tokens import ...`` resolves.
COPY yahoo_player_stats_refresher/handler.py ./handler.py
COPY yahoo_player_stats_refresher/utils.py ./utils.py
COPY common ./common

CMD ["python", "handler.py"]
