FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        git \
        curl \
        make \
        build-essential \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        llvm \
        libncurses5-dev \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libffi-dev \
        liblzma-dev

# setup pyenv
RUN git clone https://github.com/pyenv/pyenv.git /pyenv
ENV PYENV_ROOT /pyenv
ENV PYENV_ROOT="$HOME/.pyenv"
ENV PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"
RUN /pyenv/bin/pyenv install 3.11.6 && \
    /pyenv/bin/pyenv global 3.11.6

# setup github public keys
RUN mkdir -p -m 0700 ~/.ssh && \
    ssh-keyscan github.com >> ~/.ssh/known_hosts

WORKDIR /src

COPY pyproject.toml pyproject.toml

RUN python -m venv venv
ENV PATH="venv/bin:$PATH"

RUN --mount=type=ssh \
    python -m pip install pdm && \
    pdm install

COPY sqc sqc

# exec hack used for proper handling of signals
CMD exec pdm run main
