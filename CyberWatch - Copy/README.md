<<<<<<< HEAD
# CyberWatch

CyberWatch is a real-time cyber-threat awareness dashboard. It collects public threat-intelligence and cybersecurity-news feeds, normalizes the reports into a local database, and shows them on an interactive 3D globe with a live activity feed, severity indicators, and event details.

## What it does

- Collects advisories and cybersecurity news from sources including CISA, NVD, AlienVault OTX, GitHub Advisories, BleepingComputer, The Hacker News, Dark Reading, Krebs on Security, Infosecurity Magazine, The Record, and NetSec.
- Normalizes incoming reports into consistent threat events and enriches them with geographic and vendor context.
- Stores events in a local SQLite database.
- Schedules recurring feed updates and pushes new events to the dashboard through a WebSocket connection.
- Displays attacks, alerts, statistics, and explanatory summaries in an interactive web interface.

## Project structure

```text
CyberWatch/
├── backend/
│   ├── bytecode/       # Compiled Python 3.13 application core
│   ├── feeds/          # Feed collectors and RSS processing
│   ├── enrichment/     # Geo-location and AI/content enrichment helpers
│   └── run_server.py   # Backend launcher
├── frontend/
│   ├── index.html      # Dashboard page
│   └── static/         # JavaScript, CSS, and frontend settings
├── scripts/
│   └── probe_servers.py # Local server health check
├── .env.example        # Safe template for optional API keys
└── requirements.txt    # Python packages needed to run the project
```

`cyberwatch.db` and `.env` are created or kept locally and are intentionally excluded from GitHub because they can contain collected data and private API keys.

## Run locally

This project must use **Python 3.13** because the central backend files were provided as Python 3.13 bytecode.

1. Create a `.env` file from `.env.example` and add any API keys you have. The application can still start without optional keys, but some feeds or enrichment features may be limited.
2. Install the dependencies:

   ```powershell
   py -3.13 -m pip install -r requirements.txt
   ```

3. Start the backend from the project root:

   ```powershell
   py -3.13 backend/run_server.py
   ```

4. In a second terminal, start the dashboard:

   ```powershell
   py -3.13 -m http.server 5173 --directory frontend
   ```

5. Open `http://127.0.0.1:5173` in your browser.

The API runs at `http://127.0.0.1:8000` and the live event socket is available at `/events/live`.

## Important note

The core backend modules were supplied only as compiled `.pyc` files. They run normally with Python 3.13, but their original `.py` source files are not present, so those modules cannot be meaningfully edited or reviewed in GitHub. Ask the original author for the source files before making major backend changes.
=======
# Cyber-Watch
>>>>>>> 4ca6b519526d88bd4c176189716c36a0a492112b
