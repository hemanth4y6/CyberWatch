# CyberWatch – Real-Time Cyber Threat Intelligence & Visualization Platform

CyberWatch is a real-time cybersecurity awareness dashboard that collects public threat-intelligence feeds, normalizes incoming reports, and visualizes global cyber activity through an interactive web interface.

The platform helps users monitor emerging vulnerabilities, security advisories, malware activity, and cyberattack reports from trusted sources in one unified dashboard. With live updates, severity indicators, geographic context, and detailed event summaries, CyberWatch makes threat intelligence easier to understand and act upon.

## Features

### Real-Time Threat Intelligence Engine

- Collects cybersecurity alerts and advisories from multiple public sources
- Normalizes different feed formats into consistent threat-event records
- Tracks vulnerabilities, exploits, malware, breaches, and security news
- Stores collected intelligence locally using SQLite

### Live Cyberattack Visualization

- Displays global cyber-threat activity on an interactive 3D globe
- Highlights incident locations, affected regions, and threat categories
- Shows active-threat counts, top threat types, and frequently targeted locations
- Includes a live replay view of recent security activity

### Threat Feed Aggregation

CyberWatch aggregates reports from sources such as:

- CISA Advisories
- National Vulnerability Database (NVD)
- AlienVault Open Threat Exchange (OTX)
- GitHub Security Advisories
- BleepingComputer
- The Hacker News
- Dark Reading
- Krebs on Security
- Infosecurity Magazine
- The Record
- NetSec

### Enrichment and Contextual Analysis

- Adds geographic and vendor context to incoming threat reports
- Supports AI-powered summaries for clearer, human-readable explanations
- Provides detailed event information through the dashboard interface
- Helps users quickly understand the relevance and severity of emerging threats

### Live Dashboard Updates

- Uses WebSocket connections to push newly collected events to the frontend
- Automatically refreshes threat feeds on a schedule
- Displays connection status and latest synchronization time
- Provides a responsive, modern security-operations-style interface

## Tech Stack

### Frontend

- HTML
- CSS
- JavaScript
- Interactive 3D globe visualization
- WebSocket-based live event updates

### Backend

- Python
- FastAPI
- Uvicorn
- APScheduler
- SQLite

### Data and Enrichment

- RSS and public threat-intelligence feeds
- HTTPX and Feedparser
- Geographic enrichment utilities
- Optional Groq AI integration for threat summaries

## Project Structure

```text
CyberWatch/
│
├── backend/
│   ├── feeds/              # Threat-intelligence and cybersecurity-news collectors
│   ├── enrichment/         # AI, geographic, and content-enrichment helpers
│   ├── bytecode/           # Compiled backend application modules
│   └── run_server.py       # Backend server launcher
│
├── frontend/
│   ├── index.html          # Main dashboard interface
│   └── static/             # Frontend CSS, JavaScript, and configuration
│
├── scripts/
│   └── probe_servers.py    # Local server health-check utility
│
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

## How It Works

1. CyberWatch collects intelligence from public cybersecurity feeds.
2. Incoming reports are normalized into a common event format.
3. Events are enriched with relevant geographic, vendor, and contextual information.
4. Threat data is stored locally in an SQLite database.
5. New events are delivered to the dashboard through WebSocket connections.
6. Users monitor cyber activity, vulnerabilities, and alerts through the live 3D visualization.

## Running the Project Locally

1. Install Python 3.13.
2. Install the required packages:

```powershell
py -3.13 -m pip install -r requirements.txt
```

3. Start the backend server:

```powershell
py -3.13 backend/run_server.py
```

4. Start the frontend server:

```powershell
py -3.13 -m http.server 5173 --directory frontend
```

5. Open `http://127.0.0.1:5173` in your browser.

The backend API runs at `http://127.0.0.1:8000`, and live events are available through the `/events/live` WebSocket route.

## Use Cases

- Cybersecurity threat awareness
- Vulnerability and advisory monitoring
- Security operations dashboard demonstrations
- Cyber-threat research and education
- Real-time global incident visualization
- Centralized monitoring of public security intelligence

## Future Improvements

- User authentication and role-based access
- Cloud database and persistent analytics storage
- Advanced filtering by region, severity, vendor, and threat type
- Alert notifications through email, Slack, or SMS
- Historical threat analytics and trend reporting
- Expanded AI-generated risk explanations
- Deployment to cloud platforms such as Render, AWS, or Azure
