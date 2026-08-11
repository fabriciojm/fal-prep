# Base image
FROM mcr.microsoft.com/devcontainers/python:3.12

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        git \
        vim \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

# Copy latest mise image
COPY --from=jdxcode/mise /usr/local/bin/mise /usr/local/bin/

RUN pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt

RUN echo 'eval "$(mise activate bash)"' >> /home/vscode/.bashrc && \
    echo 'eval "$(mise activate zsh)"' >> /home/vscode/.zshrc

CMD ["sleep", "infinity"]
