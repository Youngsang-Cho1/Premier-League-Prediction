"""Gunicorn production config.

The app's prediction path is CPU-bound (scikit-learn) but fast (~20ms) and
the model is loaded once per worker, so a small number of workers each with
a few threads handles concurrent requests comfortably without exhausting the
memory of a small instance (each worker holds its own copy of the model).

All values are env-overridable so the same image runs on different plans.
"""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5001')}"

# Workers: keep low — each loads the model into memory. 2 is plenty for a
# portfolio deploy on a small instance; bump WEB_CONCURRENCY on bigger plans.
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))

# Threads absorb bursts of concurrent requests within a worker (predictions
# are short, and I/O-bound routes like /api/schedule benefit while waiting on
# the FPL API).
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# Kill and replace a worker if a request hangs (e.g. a stuck external call)
# instead of letting it block forever.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 30

# Recycle workers periodically to bound any slow memory growth.
max_requests = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog = "-"
