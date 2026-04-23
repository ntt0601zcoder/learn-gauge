FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies:
#   build-essential, gcc     -> compile wheels (shap, etc.)
#   git                      -> pip install git+https:// for ml-clo
#   default-libmysqlclient-dev, pkg-config -> MySQL client headers
#   libgomp1                 -> runtime lib for scikit-learn
#   curl                     -> healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        git \
        default-libmysqlclient-dev \
        pkg-config \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "learngauge.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", \
     "--timeout", "300", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
