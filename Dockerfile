FROM ubuntu:jammy-20240227 as base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:ondrej/php && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
            vim \
            default-jre \
            git \
            curl \
            make \
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
            liblzma-dev \
            php5.6 \
            build-essential git wget \
            php5.6-gd php5.6-mysql php5.6-imap php5.6-curl \
            php5.6-intl php5.6-pspell php5.6-recode php5.6-sqlite3 php5.6-tidy \
            php5.6-xmlrpc php5.6-xsl php5.6-zip php5.6-mbstring php5.6-soap \
            php5.6-opcache libicu-dev php5.6-common php5.6-json php5.6-readline \
            php5.6-xml libapache2-mod-php5.6 php5.6-cli

RUN mkdir /molprobity

WORKDIR /molprobity

RUN mkdir -p modules/chem_data

WORKDIR /molprobity/modules/chem_data

RUN git clone --depth 1 https://github.com/phenix-project/geostd.git && \
    git clone --depth 1 https://github.com/rlabduke/mon_lib.git && \
    git clone --depth 1 https://github.com/rlabduke/rotarama_data.git && \
    git clone --depth 1 https://github.com/rlabduke/cablam_data.git

RUN mkdir rama_z && \
    wget --progress=dot:giga -O rama_z/top8000_rama_z_dict.pkl \
            https://github.com/rlabduke/reference_data/raw/master/Top8000/rama_z/top8000_rama_z_dict.pkl

WORKDIR /molprobity

RUN wget --progress=dot:giga -O bootstrap.py https://github.com/cctbx/cctbx_project/raw/master/libtbx/auto_build/bootstrap.py && \
    python3 bootstrap.py --builder=molprobity --use-conda --nproc=6

WORKDIR /molprobity/molprobity
RUN ./setup.sh || true

FROM base

RUN useradd -ms /bin/bash sqc && \
    mkdir /pyenv && \
    mkdir /src && \
    chown sqc /src

# setup pyenv
RUN git clone https://github.com/pyenv/pyenv.git /pyenv
ENV PYENV_ROOT /pyenv
ENV PYENV_ROOT="$HOME/.pyenv"
ENV PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"
RUN /pyenv/bin/pyenv install 3.11.6 && \
    /pyenv/bin/pyenv global 3.11.6

USER sqc

ENV PATH="${PATH}:/molprobity/molprobity/cmdline/"
ENV PATH="${PATH}:/BeEM/bin/"

WORKDIR /src

COPY pyproject.toml pyproject.toml

RUN python -m venv venv
ENV PATH="venv/bin:$PATH"

RUN python -m pip install --no-cache-dir pdm==2.12.4 && \
    pdm install

COPY sqc sqc

# exec hack used for proper handling of signals
CMD exec pdm run main
