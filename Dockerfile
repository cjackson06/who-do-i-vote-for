FROM ubuntu:24.04

# Install uv
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev musl-dev

# Install dependencies
WORKDIR /app
COPY uv.lock .
COPY pyproject.toml .
RUN uv sync

COPY my_politician/ my_politician/
COPY political_profiler/ political_profiler/

CMD ["uv", "run", "adk", "api_server", "--allow_origins", "*"]
