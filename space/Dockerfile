# Hugging Face Space (Docker). Builds the aicad web app with FreeCAD for drawings and FEA.
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        freecad-python3 libgl1 libglu1-mesa libxrender1 libxcursor1 libxft2 libxinerama1 \
        calculix-ccx gmsh ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

COPY --chown=user pyproject.toml README.md ./
COPY --chown=user aicad ./aicad
RUN pip install --user --no-cache-dir "cadquery>=2.4"

# freecad-python3 installs the command as /usr/lib/freecad/bin/freecadcmd-python3 and puts
# nothing in /usr/bin, so point the tool straight at it. Verified against the Debian bookworm
# file list for that package.
ENV FREECAD_CMD=/usr/lib/freecad/bin/freecadcmd-python3
EXPOSE 7860
CMD ["python", "-m", "aicad.web", "--host", "0.0.0.0", "--port", "7860"]
