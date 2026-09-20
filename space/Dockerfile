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

ENV AICAD_OUT=/home/user/app/out
EXPOSE 7860
CMD ["python", "-m", "aicad.web", "--host", "0.0.0.0", "--port", "7860"]
