# Runs the monthly CAR-T data pipeline in the same order as
# .github/workflows/monthly_update.yml.
#
# Build:  docker build -t cart-pipeline .
# Run:    docker run --rm -v "$(pwd)/data:/app/data" -v "$(pwd)/xhs_cards:/app/xhs_cards" cart-pipeline

FROM python:3.12-slim

# CJK fonts for the Chinese chart labels in the infographic scripts.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY python/ python/
COPY data/ data/
COPY README.md .

CMD ["sh", "-c", "\
python python/fetch_cart_data.py && \
python python/fix_phase_labels.py && \
python python/update_treatment_data_2026.py && \
python python/generate_trial_figures.py && \
python python/update_readme.py"]
