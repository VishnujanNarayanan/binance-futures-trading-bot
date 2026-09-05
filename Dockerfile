# Runs the bot without a local Python install or virtualenv.
#
#   docker build -t trading-bot .
#   docker run --rm -it --env-file .env trading-bot                    # interactive menu
#   docker run --rm --env-file .env trading-bot --action positions     # headless
#
# Interactive mode needs a TTY, hence -it. Headless mode does not.

FROM python:3.12-slim

# Dependencies are installed before the source is copied so that editing a module
# does not invalidate the pip layer.
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY trading_bot/ ./trading_bot/

# cli.py imports its own package as top-level `bot.*`, so the process has to start
# inside trading_bot/ -- the same constraint the README documents for a local run.
WORKDIR /app/trading_bot

# Logs go to a directory of their own so it can be bind-mounted out:
#   docker run --rm -v "$PWD/logs:/app/logs" ... trading-bot --action positions
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TRADING_BOT_LOG=/app/logs/trading.log

RUN useradd --create-home --uid 10001 bot \
    && mkdir -p /app/logs \
    && chown -R bot:bot /app
USER bot

VOLUME ["/app/logs"]

ENTRYPOINT ["python", "cli.py"]
