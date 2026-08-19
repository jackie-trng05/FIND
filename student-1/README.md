# Student 1 placeholder

This directory contains the placeholder backend service for Student 1.

Run locally (from repository root)
1. Build and start the integrated application: docker compose up --build
2. The Student 1 backend will be available at http://localhost:16005/
3. Health endpoint: http://localhost:16005/health (returns {"status":"ok"})

Important: the backend runs on the host-mapped port 16005. The container-internal port is 5001, which is not the browser URL. If `localhost` is not resolving correctly in your environment, use `127.0.0.1:16005` instead.
