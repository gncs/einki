FROM debian:12-slim

ARG ANKICONNECT_VERSION=25.2.25.0
ARG ANKI_VERSION=25.02.4
ARG QT_VERSION=6

RUN apt-get update && apt-get install --no-install-recommends -y \
        wget zstd locales curl ca-certificates jq \
        # mpv is needed for audio cards AND transitively provides many
        # graphics libs (libGL, libEGL, etc.) that Qt6/Anki requires.
        mpv \
        libglib2.0-0 libgl1 libegl1 libxcb-xinerama0 libxcb-cursor0 libnss3 \
        libxcomposite-dev libxdamage-dev libxtst-dev libxkbcommon-dev libxkbfile-dev \
        libfontconfig1 libdbus-1-3 && \
    apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* && \
    useradd -m anki

# Anki installation
RUN mkdir /app && chown -R anki /app
COPY startup.sh /app/startup.sh
WORKDIR /app

RUN wget -O ANKI.tar.zst \
        https://github.com/ankitects/anki/releases/download/${ANKI_VERSION}/anki-${ANKI_VERSION}-linux-qt${QT_VERSION}.tar.zst && \
    zstd -d ANKI.tar.zst && rm ANKI.tar.zst && \
    tar xf ANKI.tar && rm ANKI.tar
WORKDIR /app/anki-${ANKI_VERSION}-linux-qt${QT_VERSION}

# Run modified install.sh (skip xdg-mime which requires a desktop)
RUN sed 's/xdg-mime/#/' install.sh | sh -

# Locale setup
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=en_US.UTF-8
ENV LANG=en_US.UTF-8 LANGUAGE=en_US LC_ALL=en_US.UTF-8

# Anki data
COPY data /data
RUN mkdir -p /data/addons21 && chown -R anki /data

# AnkiConnect plugin
WORKDIR /app
RUN curl -L https://git.sr.ht/~foosoft/anki-connect/archive/${ANKICONNECT_VERSION}.tar.gz | \
    tar -xz && \
    mv anki-connect-${ANKICONNECT_VERSION} anki-connect && \
    chown -R anki:anki /app/anki-connect/plugin && \
    ln -s -f /app/anki-connect/plugin /data/addons21/AnkiConnectDev

# Bind AnkiConnect to all interfaces so the host can reach it
RUN jq '.webBindAddress = "0.0.0.0"' /data/addons21/AnkiConnectDev/config.json > tmp_file && \
    mv tmp_file /data/addons21/AnkiConnectDev/config.json

USER anki

ENV ANKICONNECT_WILDCARD_ORIGIN="0"
ENV QMLSCENE_DEVICE=softwarecontext
ENV FONTCONFIG_PATH=/etc/fonts
ENV QT_XKB_CONFIG_ROOT=/usr/share/X11/xkb
ENV QT_QPA_PLATFORM="vnc"

EXPOSE 8765 5900

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8765 -d '{"action":"version","version":6}' || exit 1

VOLUME /data

CMD ["/bin/bash", "startup.sh"]
