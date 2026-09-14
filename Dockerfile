# ----------------------------------------------------------------------
# Image Docker pour le bot Discord (compatible Railway)
# ----------------------------------------------------------------------
# Pygame nécessite des libs SDL natives. Railway tourne sur des conteneurs
# Debian slim ; on installe donc les dépendances système pour SDL + dummy
# (driver sans affichage) afin que Pygame puisse générer des images PNG
# sans écran physique.
# ----------------------------------------------------------------------
FROM python:3.11-slim

# Variables d'environnement pour Pygame en mode headless
ENV PYTHONUNBUFFERED=1 \
    SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=dummy \
    PYTHONDONTWRITEBYTECODE=1

# Dépendances système pour Pygame (SDL, image, font, ttf, gfx)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libfreetype6-dev \
        libjpeg-dev \
        libpng-dev \
        libsdl2-dev \
        libsdl2-image-dev \
        libsdl2-mixer-dev \
        libsdl2-ttf-dev \
        libsdl2-gfx-dev \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail (Railway monte le code dans /app)
WORKDIR /app

# Installation des dépendances Python (cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Railway expose le port via $PORT ; le bot Discord n'en a pas besoin,
# mais on l'expose quand même pour respecter la convention Railway.
EXPOSE 8000

# Commande de lancement
CMD ["python", "discord_bot.py"]
