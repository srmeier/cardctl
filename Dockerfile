FROM nvidia/cuda:12.6.1-devel-ubuntu24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev python3-venv \
    && rm -rf /var/lib/apt/lists/*
COPY . /cardctl
WORKDIR /cardctl
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126 && \
    pip install -r requirements.txt
CMD [                               \
    "gunicorn",                     \
    "--worker-tmp-dir", "/dev/shm", \
    "--timeout", "1000",            \
    "--bind", "0.0.0.0:8000",       \
    "--workers", "4",               \
    "cardctl.wsgi:application"      \
]
