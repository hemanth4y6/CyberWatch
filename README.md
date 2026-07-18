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

