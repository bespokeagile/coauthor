FROM python:3.10-slim
LABEL maintainer="BespokeAgile"
LABEL description="Bespoke Coauthor -- open-source code authorship analysis"
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY . ./
RUN pip install --no-cache-dir ".[web]"
VOLUME /root/.coauthor
EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:8002/health || exit 1
CMD ["bespoke-coauthor", "serve", "--host", "0.0.0.0", "--port", "8002"]
