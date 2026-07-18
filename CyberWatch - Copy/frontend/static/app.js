/**
 * app.js — CyberWatch frontend logic.
 *
 * Responsibilities:
 *  - Globe.gl initialization + arc/point rendering
 *  - WebSocket client with exponential backoff
 *  - Cinematic drip engine (300 – 2000 ms randomized release)
 *  - Live feed panel (max 200 entries)
 *  - Side panel with 3 layers + AI summary
 *  - Stats bar polling every 60 s
 *  - Null-coordinate guard (CISA/NVD events silently skipped on globe)
 */

'use strict';

// ── Constants ─────────────────────────────────────────────────────────────────

const ATTACK_ICONS = {
  'Ransomware':  '🔒',
  'Exploit':     '⚡',
  'Phishing':    '🎣',
  'DDoS':        '🌊',
  'Malware':     '🐛',
  'Data Breach': '📂',
  'Brute Force': '🔨',
  'APT':         '🎯',
  'Zero-Day':    '💥',
  'Supply Chain':'🔗',
  'Vulnerability':'🛡️',
  'Critical Vulnerability':'🛡️',
  'Espionage':   '🕵️',
  'Nation-State': '🏴',
  'Social Engineering':'🎭',
  'Botnet':      '🤖',
  'Credential Theft':'🔑',
  'Insider Threat':'👤',
  'Unknown':     '⚠️',
};

function getFlagEmoji(countryCode) {
  if (!countryCode || countryCode.length !== 2) return '🌍';
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map(char => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
}

const SEV_COLORS = {
  'Critical': '#ff3b3b',
  'High':     '#ff7a1a',
  'Medium':   '#f5c842',
  'Low':      '#22c97a',
};

const WHAT_THIS_MEANS = {
  'Ransomware': {
    oneliner: "Attackers encrypted the target's systems and demanded payment to restore access.",
    foryou: "This doesn't steal your data directly — it can cut off access to services you depend on.",
    highcon: "A major ransomware attack can shut down hospitals, pipelines, or financial systems for days."
  },
  'Exploit': {
    oneliner: "Hackers used a known software flaw to break into a secure network.",
    foryou: "Your personal info can be exposed if companies you use fail to patch their systems.",
    highcon: "Exploits allow threat actors to bypass security seamlessly, leading to massive breaches."
  },
  'Phishing': {
    oneliner: "Attackers tricked employees into handing over their passwords via a fake email.",
    foryou: "It only takes one convincing email for attackers to access your private accounts.",
    highcon: "Phishing is the #1 way corporate networks are breached, often acting as a gateway for ransomware."
  },
  'DDoS': {
    oneliner: "A massive flood of fake traffic knocked a website or service offline.",
    foryou: "Services you rely on (like banking or gaming) become temporarily unavailable.",
    highcon: "DDoS attacks are often used as a distraction while attackers breach other parts of the network."
  },
  'Malware': {
    oneliner: "Malicious software was installed to spy on users or steal critical data.",
    foryou: "Your devices could be infected, exposing your passwords and tracking your activity.",
    highcon: "Advanced malware acts as a backdoor, giving foreign governments persistent access to critical infrastructure."
  },
  'Data Breach': {
    oneliner: "Attackers stole sensitive databases containing personal or corporate information.",
    foryou: "Your passwords, emails, or credit card numbers may now be sold on the dark web.",
    highcon: "Stolen data fuels identity theft rings and allows nation-states to conduct targeted espionage."
  },
  'Brute Force': {
    oneliner: "Automated scripts relentlessly guessed passwords until they broke in.",
    foryou: "If you reuse simple passwords, attackers will eventually gain access to your accounts.",
    highcon: "Brute force attacks exploit weak corporate password policies to compromise administrative control."
  },
  'Unknown': {
    oneliner: "Suspicious cyber activity was detected without clear attribution to a specific method.",
    foryou: "Be cautious—your online footprint may be affected if the situation escalates.",
    highcon: "Many attacks go unclassified until forensic investigations uncover the root cause."
  }
};

const MAX_FEED   = 200;
const MAX_ARCS   = 200;
const MAX_POINTS = 300;

// Country names (ISO-2 → name)
const COUNTRY_NAMES = {
  AF:'Afghanistan',AL:'Albania',DZ:'Algeria',AD:'Andorra',AO:'Angola',AR:'Argentina',AM:'Armenia',
  AU:'Australia',AT:'Austria',AZ:'Azerbaijan',BH:'Bahrain',BD:'Bangladesh',BY:'Belarus',BE:'Belgium',
  BJ:'Benin',BT:'Bhutan',BO:'Bolivia',BA:'Bosnia and Herzegovina',BW:'Botswana',BR:'Brazil',
  BN:'Brunei',BG:'Bulgaria',BF:'Burkina Faso',BI:'Burundi',KH:'Cambodia',CM:'Cameroon',CA:'Canada',
  CF:'Central African Republic',TD:'Chad',CL:'Chile',CN:'China',CO:'Colombia',CD:'DR Congo',
  CG:'Congo',CR:'Costa Rica',HR:'Croatia',CU:'Cuba',CY:'Cyprus',CZ:'Czechia',DK:'Denmark',
  DJ:'Djibouti',EC:'Ecuador',EG:'Egypt',SV:'El Salvador',GQ:'Equatorial Guinea',ER:'Eritrea',
  EE:'Estonia',SZ:'Eswatini',ET:'Ethiopia',FI:'Finland',FR:'France',GA:'Gabon',GM:'Gambia',
  GE:'Georgia',DE:'Germany',GH:'Ghana',GR:'Greece',GT:'Guatemala',GN:'Guinea',GY:'Guyana',
  HT:'Haiti',HN:'Honduras',HU:'Hungary',IS:'Iceland',IN:'India',ID:'Indonesia',IR:'Iran',
  IQ:'Iraq',IE:'Ireland',IL:'Israel',IT:'Italy',JM:'Jamaica',JP:'Japan',JO:'Jordan',KZ:'Kazakhstan',
  KE:'Kenya',KP:'North Korea',KR:'South Korea',KW:'Kuwait',KG:'Kyrgyzstan',LA:'Laos',LV:'Latvia',
  LB:'Lebanon',LS:'Lesotho',LR:'Liberia',LY:'Libya',LT:'Lithuania',LU:'Luxembourg',MG:'Madagascar',
  MW:'Malawi',MY:'Malaysia',ML:'Mali',MT:'Malta',MR:'Mauritania',MX:'Mexico',MD:'Moldova',
  MN:'Mongolia',ME:'Montenegro',MA:'Morocco',MZ:'Mozambique',MM:'Myanmar',NA:'Namibia',NP:'Nepal',
  NL:'Netherlands',NZ:'New Zealand',NI:'Nicaragua',NE:'Niger',NG:'Nigeria',MK:'North Macedonia',
  NO:'Norway',OM:'Oman',PK:'Pakistan',PA:'Panama',PG:'Papua New Guinea',PY:'Paraguay',PE:'Peru',
  PH:'Philippines',PL:'Poland',PS:'Palestine',PT:'Portugal',QA:'Qatar',RO:'Romania',RU:'Russia',RW:'Rwanda',
  SA:'Saudi Arabia',SN:'Senegal',RS:'Serbia',SL:'Sierra Leone',SG:'Singapore',SK:'Slovakia',
  SI:'Slovenia',SO:'Somalia',ZA:'South Africa',SS:'South Sudan',ES:'Spain',LK:'Sri Lanka',
  SD:'Sudan',SR:'Suriname',SE:'Sweden',CH:'Switzerland',SY:'Syria',TW:'Taiwan',TJ:'Tajikistan',
  TZ:'Tanzania',TH:'Thailand',TL:'Timor-Leste',TG:'Togo',TT:'Trinidad and Tobago',TN:'Tunisia',
  TR:'Turkey',TM:'Turkmenistan',UG:'Uganda',UA:'Ukraine',AE:'UAE',GB:'United Kingdom',
  US:'United States',UY:'Uruguay',UZ:'Uzbekistan',VE:'Venezuela',VN:'Vietnam',YE:'Yemen',
  ZM:'Zambia',ZW:'Zimbabwe'
};

function getCountryName(code) {
  if (!code) return 'Unknown';
  return COUNTRY_NAMES[code.toUpperCase()] || code;
}

// ── State ─────────────────────────────────────────────────────────────────────

let globe;
let arcsData   = [];
let pointsData = [];
let eventQueue = [];
let wsDelay    = 1000;
let ws;

let countryPolygons = [];
let heatmapData = [];
let heatmapMap  = new Map();  // ISO-2 → {country, score, ...} for O(1) lookup
let heatmapPulse = 0;     // oscillates 0→1→0 for heatmap glow
let autoFlyEnabled = true; // auto-fly to critical events
let hoveredCountry = null; // ISO-2 code of currently hovered country polygon

// ── Helpers ───────────────────────────────────────────────────────────────────

function ageMinutes(ts) {
  return (Date.now() - new Date(ts)) / 60_000;
}

function dotColor(event) {
  return severityColor(event.severity);
}

function severityColor(sev) {
  return SEV_COLORS[sev] || '#4a4a66';
}

function timeAgo(ts) {
  if (!ts) return 'Unknown';
  const s = (Date.now() - new Date(ts)) / 1000;
  if (s < 60)   return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400)return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function cvssText(score) {
  if (score === null || score === undefined) return 'No CVSS score available for this event.';
  if (score >= 9.0) return `Score ${score} — Critical. Severe vulnerability; exploitation may cause catastrophic damage. Patch immediately.`;
  if (score >= 7.0) return `Score ${score} — High. Exploitable remotely, likely without authentication.`;
  if (score >= 4.0) return `Score ${score} — Medium. Exploitation requires some conditions; still poses real risk.`;
  return `Score ${score} — Low. Limited impact; monitoring recommended.`;
}

// ── Globe ─────────────────────────────────────────────────────────────────────

function heatmapColor(iso, pulse) {
  const isHovered = iso === hoveredCountry;
  const match = heatmapMap.get(iso);
  if (match) {
    const score = match.score || 0;
    // Pulse factor: oscillate alpha by ±0.08 for high-score countries
    const p = score >= 61 ? pulse * 0.08 : 0;
    // Hover glow: boost alpha and shift toward brighter tint
    if (isHovered) {
      if (score >= 86) return `rgba(255, 80, 80, 0.65)`;
      if (score >= 61) return `rgba(240, 120, 60, 0.50)`;
      return `rgba(100, 160, 255, 0.35)`;
    }
    if (score >= 86) return `rgba(220, 50, 50, ${0.45 + p})`;
    if (score >= 61) return `rgba(200, 80, 40, ${0.30 + p})`;
  }
  // Hover glow for countries with no CARS data
  if (isHovered) return `rgba(100, 160, 255, 0.30)`;
  return 'rgba(180, 185, 195, 0.12)';
}

function initGlobe() {
  const wrap = document.getElementById('globe-wrap');

  globe = Globe()
    // Conflictly-style dark earth texture with blue palette
    .globeImageUrl('//unpkg.com/three-globe/example/img/earth-dark.jpg')
    .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
    .backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png')
    .atmosphereColor('#1a4aad')
    .atmosphereAltitude(0.18)
    // Points (source/target)
    .pointsData([])
    .pointLat('lat')
    .pointLng('lng')
    .pointColor('color')
    .pointAltitude(0.015)
    .pointRadius(0.4)
    .pointsMerge(false)
    .onPointClick(ev => openPopup(ev))
    // Polygons (Heatmap)
    .polygonsData([])
    .polygonCapColor(d => heatmapColor(d.properties?.ISO_A2, heatmapPulse))
    .polygonSideColor(() => 'rgba(0,0,0,0)')
    .polygonStrokeColor(() => 'rgba(255,255,255,0.22)')
    .polygonAltitude(d => d.properties?.ISO_A2 === hoveredCountry ? 0.014 : 0.006)
    .onPolygonHover(hoverD => {
      hoveredCountry = hoverD ? hoverD.properties?.ISO_A2 : null;
      globe.polygonCapColor(d => heatmapColor(d.properties?.ISO_A2, heatmapPulse));
      globe.polygonAltitude(d => d.properties?.ISO_A2 === hoveredCountry ? 0.014 : 0.006);
    })
    .onPolygonClick(d => {
      const cc = d.properties?.ISO_A2;
      const lat = d.properties.LABEL_Y || 0;
      const lng = d.properties.LABEL_X || 0;
      if (lat && lng) globe.pointOfView({ lat, lng, altitude: 1.5 }, 600);
      if (cc) openCountryOverlay(cc);
    })
    (wrap);

  fetch('https://unpkg.com/globe.gl/example/datasets/ne_110m_admin_0_countries.geojson')
    .then(r => r.json())
    .then(data => {
      countryPolygons = data.features;
      globe.polygonsData(countryPolygons);
    });

  // Auto-rotation
  const controls = globe.controls();
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.3;
  // Pause auto-rotation on user interaction, resume after 8s idle
  let idleTimer = null;
  const pauseRotation = () => {
    controls.autoRotate = false;
    autoFlyEnabled = false;
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      controls.autoRotate = true;
      autoFlyEnabled = true;
    }, 8000);
  };
  wrap.addEventListener('mousedown', pauseRotation);
  wrap.addEventListener('touchstart', pauseRotation, { passive: true });
  wrap.addEventListener('wheel', pauseRotation, { passive: true });

  // Animated heatmap pulse — use requestAnimationFrame for smoother, more efficient animation
  let lastPulseUpdate = 0;
  function animatePulse(timestamp) {
    // Throttle to ~60ms intervals (~16fps for subtle pulse — saves CPU vs the full 60fps)
    if (timestamp - lastPulseUpdate > 60) {
      heatmapPulse = (Math.sin(Date.now() / 800) + 1) / 2;
      if (globe && countryPolygons.length > 0) {
        globe.polygonCapColor(d => heatmapColor(d.properties?.ISO_A2, heatmapPulse));
      }
      lastPulseUpdate = timestamp;
    }
    requestAnimationFrame(animatePulse);
  }
  requestAnimationFrame(animatePulse);

  // Resize — debounced to avoid excessive recalculations
  const resize = () => globe.width(wrap.clientWidth).height(wrap.clientHeight);
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 100);
  });
  resize();

  // Hide loading overlay after globe textures load (~1 s grace)
  setTimeout(() => {
    document.getElementById('loading-overlay').classList.add('gone');
  }, 1400);
}

// ── WebSocket ─────────────────────────────────────────────────────────────────

function connectWS() {
  try {
    ws = new WebSocket(CONFIG.WS_URL);

    ws.onopen = () => {
      wsDelay = 1000;
      setStatus('live');
    };

    ws.onmessage = ({ data }) => {
      let ev;
      try { ev = JSON.parse(data); } catch { return; }
      if (ev.type === 'ping') return;
      eventQueue.push(ev);
    };

    ws.onerror = () => setStatus('reconnecting');
    ws.onclose = () => {
      setStatus('reconnecting');
      setTimeout(connectWS, wsDelay);
      wsDelay = Math.min(wsDelay * 2, 30_000);
    };
  } catch {
    setTimeout(connectWS, wsDelay);
    wsDelay = Math.min(wsDelay * 2, 30_000);
  }
}

function setStatus(state) {
  const el = document.getElementById('ws-status');
  if (state === 'live') {
    el.textContent  = '● LIVE';
    el.className    = 'status-live';
  } else {
    el.textContent  = '● RECONNECTING';
    el.className    = 'status-reconnecting';
  }
}

// ── Cinematic drip ────────────────────────────────────────────────────────────

function startDrip() {
  function drop() {
    if (eventQueue.length > 0) {
      renderEvent(eventQueue.shift());
    }
    const delay = eventQueue.length > 0
      ? 300 + Math.random() * 1700
      : 800;
    setTimeout(drop, delay);
  }
  drop();
}

// ── Globe rendering ───────────────────────────────────────────────────────────

function renderEvent(event) {
  const hasSrc = event.source_lat != null && event.source_lng != null;
  const hasTgt = event.target_lat != null && event.target_lng != null;

  if (hasSrc || hasTgt) {
    const lat = hasTgt ? event.target_lat : event.source_lat;
    const lng = hasTgt ? event.target_lng : event.source_lng;
    
    const pt = {
      ...event,
      lat:   lat,
      lng:   lng,
      color: dotColor(event),
    };
    pointsData = [...pointsData.slice(-(MAX_POINTS - 1)), pt];
    globe.pointsData(pointsData);

    // Auto-fly to Critical/High events
    if (autoFlyEnabled && (event.severity === 'Critical' || event.severity === 'High')) {
      globe.pointOfView({ lat, lng, altitude: 2.0 }, 1200);
    }
  }
}

// ── Country Dashboard Overlay ─────────────────────────────────────────────────

function openCountryOverlay(cc) {
  const overlay = document.getElementById('country-overlay');
  if (!overlay) return;

  const name = getCountryName(cc);
  document.getElementById('co-flag').textContent = getFlagEmoji(cc);
  document.getElementById('co-name').textContent = name;

  // Reset
  document.getElementById('co-score-val').textContent = '…';
  document.getElementById('co-score-fill').style.width = '0%';
  document.getElementById('co-cars-badge').textContent = '…';
  document.getElementById('co-threats').innerHTML = '<span style="color:var(--text-muted);font-size:11px;">Loading…</span>';
  document.getElementById('co-events').innerHTML = '<span style="color:var(--text-muted);font-size:11px;">Loading…</span>';

  overlay.classList.remove('hidden');

  // Fetch CARS score
  fetch(`${CONFIG.API_URL}/cars/${cc}`)
    .then(r => r.json())
    .then(data => {
      const scoreEl = document.getElementById('co-score-val');
      const fillEl  = document.getElementById('co-score-fill');
      const badge   = document.getElementById('co-cars-badge');

      scoreEl.textContent = data.score?.toFixed(1) ?? '0';
      fillEl.style.width  = `${Math.min(data.score || 0, 100)}%`;
      fillEl.style.background = data.color || '#4a4a6a';

      badge.textContent = data.label || 'NORMAL';
      badge.style.color = data.color || 'var(--text-muted)';
      badge.style.background = `${data.color || '#4a4a6a'}22`;
      badge.style.border = `1px solid ${data.color || '#4a4a6a'}55`;
    })
    .catch(() => {
      document.getElementById('co-score-val').textContent = 'N/A';
    });

  // Fetch country events
  fetch(`${CONFIG.API_URL}/events/country/${cc}?limit=15`)
    .then(r => r.json())
    .then(events => {
      // Threat type breakdown
      const typeCounts = {};
      events.forEach(ev => {
        const t = ev.attack_type || 'Unknown';
        typeCounts[t] = (typeCounts[t] || 0) + 1;
      });
      const threatEl = document.getElementById('co-threats');
      if (Object.keys(typeCounts).length === 0) {
        threatEl.innerHTML = '<span style="color:var(--text-muted);font-size:11px;">No data</span>';
      } else {
        threatEl.innerHTML = Object.entries(typeCounts)
          .sort((a, b) => b[1] - a[1])
          .map(([type, count]) => {
            const icon = ATTACK_ICONS[type] || '⚠️';
            return `<span class="co-threat-pill">${icon} ${type} <span class="co-threat-count">${count}</span></span>`;
          }).join('');
      }

      // Recent events list
      const eventsEl = document.getElementById('co-events');
      if (events.length === 0) {
        eventsEl.innerHTML = '<span style="color:var(--text-muted);font-size:11px;">No events in the last 30 days</span>';
      } else {
        eventsEl.innerHTML = events.slice(0, 10).map(ev => {
          const sev = (ev.severity || 'low').toLowerCase();
          const sevColors = { critical: 'var(--accent-red)', high: 'var(--accent-orange)', medium: 'var(--accent-yellow)', low: 'var(--accent-green)' };
          const sevBg = { critical: 'rgba(255,45,45,0.15)', high: 'rgba(255,122,26,0.15)', medium: 'rgba(240,165,0,0.15)', low: 'rgba(34,201,122,0.15)' };
          const icon = ATTACK_ICONS[ev.attack_type] || '⚠️';
          return `
            <div class="co-event-item" data-event-id="${ev.id}">
              <div class="co-event-title">${icon} ${ev.description || ev.attack_type}</div>
              <div class="co-event-meta">
                <span class="co-event-sev" style="color:${sevColors[sev]};background:${sevBg[sev]}">${ev.severity}</span>
                <span>${timeAgo(ev.timestamp)}</span>
                <span>${(ev.source_feed || '').replace('_rss', '')}</span>
              </div>
            </div>`;
        }).join('');

        // Click handler for event items
        eventsEl.querySelectorAll('.co-event-item').forEach(el => {
          el.addEventListener('click', () => {
            const evId = el.dataset.eventId;
            const ev = events.find(e => e.id === evId);
            if (ev) {
              closeCountryOverlay();
              openPanel(ev);
            }
          });
        });
      }
    })
    .catch(() => {
      document.getElementById('co-events').innerHTML = '<span style="color:var(--text-muted);font-size:11px;">Failed to load</span>';
    });
}

function closeCountryOverlay() {
  const overlay = document.getElementById('country-overlay');
  if (overlay) overlay.classList.add('hidden');
}

// ── Static News Feed ──────────────────────────────────────────────────────────

async function loadStaticNews() {
  try {
    const list = document.getElementById('feed-list');
    const resp = await fetch(`${CONFIG.API_URL}/news`);
    const news = await resp.json();

    list.innerHTML = '';
    if (!news || news.length === 0) {
      list.innerHTML = '<div class="feed-empty"><div class="feed-empty-icon">📰</div><div>No critical news in the last 7 days</div></div>';
      return;
    }
    
    news.forEach(event => addToFeed(event, false));
    updateTicker(news);
  } catch { /* silent */ }
}

function updateTicker(news) {
  const ticker = document.getElementById('ticker-content');
  if (!ticker) return;
  ticker.innerHTML = '';
  if (!news || news.length === 0) return;

  // Build items
  const items = news.slice(0, 20).map(event => {
    let flag = '🌍';
    if (event.target_country) flag = getFlagEmoji(event.target_country);
    else if (event.source_country) flag = getFlagEmoji(event.source_country);

    const rawHeadline = event.description ? event.description.split('.')[0] : event.attack_type;
    const headline = rawHeadline.length > 80 ? rawHeadline.substring(0, 80) + '…' : rawHeadline;
    const time = timeAgo(event.timestamp);
    return { flag, headline, time, event };
  });

  // Duplicate for seamless infinite loop
  const renderItems = (arr) => arr.forEach(({ flag, headline, time, event }) => {
    const el = document.createElement('span');
    el.className = 'ticker-item';
    el.style.cursor = 'pointer';
    el.innerHTML = `${flag}<strong>${headline}</strong><span class="time">${time}</span><span class="ticker-sep">·</span>`;
    el.addEventListener('click', () => openPanel(event));
    ticker.appendChild(el);
  });

  renderItems(items);
  renderItems(items); // duplicate for seamless loop
}

function addToFeed(event, prepend = true) {
  const list = document.getElementById('feed-list');

  // Remove placeholder
  const empty = list.querySelector('.feed-empty');
  if (empty) empty.remove();

  const icon  = ATTACK_ICONS[event.attack_type] || '⚠️';
  const sev   = (event.severity || 'low').toLowerCase();
  const num   = prepend ? '' : `#${list.children.length + 1}`;

  let routeHtml = '';
  if (event.source_country && event.target_country) {
    routeHtml = `<div class="fe-route">${getFlagEmoji(event.source_country)} ${event.source_country} → ${getFlagEmoji(event.target_country)} ${event.target_country}</div>`;
  } else if (event.target_country) {
    routeHtml = `<div class="fe-route">Target: ${getFlagEmoji(event.target_country)} ${event.target_country}</div>`;
  } else if (event.source_country) {
    routeHtml = `<div class="fe-route">Source: ${getFlagEmoji(event.source_country)} ${event.source_country}</div>`;
  }

  const el = document.createElement('div');
  el.className = 'fe';
  el.innerHTML = `
    <div class="fe-row1">
      <span class="fe-num">${icon}</span>
      <span class="fe-title">${event.description || event.attack_type}</span>
      <span class="fe-sev ${sev}">${event.severity || 'LOW'}</span>
    </div>
    ${routeHtml}
    <div class="fe-meta-row">
      <span class="fe-source">🌐 ${(event.source_feed || '').replace('_rss','')}</span>
      <span class="fe-age">${timeAgo(event.timestamp)}</span>
    </div>
  `;

  el.dataset.ts = event.timestamp;

  el.addEventListener('click', () => {
    openPanel(event);
    if (event.source_lat) {
      globe.pointOfView(
        { lat: event.source_lat, lng: event.source_lng, altitude: 1.8 },
        900
      );
    }
  });

  if (prepend) {
    list.insertBefore(el, list.firstChild);
    while (list.children.length > MAX_FEED) list.removeChild(list.lastChild);
  } else {
    list.appendChild(el);
  }
}

// ── Side panel & Center Popup ─────────────────────────────────────────────────

let currentPopupEvent = null;

function openPopup(event) {
  currentPopupEvent = event;
  const popup = document.getElementById('center-popup');
  
  const icon = ATTACK_ICONS[event.attack_type] || '❓';
  document.getElementById('popup-icon').textContent = icon;
  
  // Add more info to popup
  const sevColor = severityColor(event.severity);
  document.getElementById('popup-type').innerHTML = `
    <span style="color:${sevColor}; border:1px solid ${sevColor}; padding:1px 4px; border-radius:3px; font-size:9px; margin-right:4px;">${event.severity || 'UNK'}</span>
    ${event.attack_type || 'Unknown'}
  `;
  
  let routeStr = '';
  if (event.source_country && event.target_country) {
    routeStr = `${event.source_country} → ${event.target_country}`;
  } else if (event.target_country) {
    routeStr = `Target: ${event.target_country}`;
  } else if (event.source_country) {
    routeStr = `Source: ${event.source_country}`;
  }
  document.getElementById('popup-src').innerHTML = `
    <div>${routeStr}</div>
    <div style="font-size:10px; color:var(--text-muted); margin-top:2px;">${timeAgo(event.timestamp)}</div>
    <div style="font-size:10px; color:var(--text-muted); margin-top:1px;">${(event.description || '').substring(0, 60)}${event.description && event.description.length > 60 ? '...' : ''}</div>
  `;
  
  popup.classList.remove('hidden');
}

function closePopup() {
  const popup = document.getElementById('center-popup');
  if (popup) popup.classList.add('hidden');
  currentPopupEvent = null;
}

function openPanel(event) {
  // Reset AI summary sections to loading state
  const aiWhat = document.getElementById('ai-what-content');
  const aiAffects = document.getElementById('ai-affects-content');
  if (aiWhat)    { aiWhat.className = 'ai-text ai-loading'; aiWhat.textContent = 'Generating…'; }
  if (aiAffects) { aiAffects.className = 'ai-text ai-loading'; aiAffects.textContent = ''; }

  fillLayer1(event);
  fillLayer2(event);
  fillLayer3(event);

  if (event.target_country) loadCARS(event.target_country);

  // Load per-event AI summary
  loadEventAISummary(event);

  document.getElementById('side-panel').classList.add('open');
}

async function loadEventAISummary(event) {
  const aiWhat     = document.getElementById('ai-what-content');
  const aiAffects  = document.getElementById('ai-affects-content');
  const aiSource   = document.getElementById('ai-source-link');
  if (!aiWhat || !aiAffects) return;

  aiWhat.className    = 'ai-text ai-loading';
  aiWhat.textContent  = 'Generating…';
  aiAffects.className = 'ai-text ai-loading';
  aiAffects.textContent = '';
  if (aiSource) aiSource.style.display = 'none';

  try {
    const resp = await fetch(`${CONFIG.API_URL}/ai-summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title:          event.description || '',
        attack_type:    event.attack_type || 'Unknown',
        severity:       event.severity    || 'Unknown',
        source_country: event.source_country || null,
        target_country: event.target_country || null,
        cve_id:         event.cve_id || null,
      })
    });
    const data = await resp.json();

    // Fix: check presence with 'in' not truthiness (how_it_affects can be empty string)
    if (data && typeof data.what_it_is === 'string') {
      aiWhat.className    = data.what_it_is ? 'ai-text' : 'ai-error';
      aiWhat.textContent  = data.what_it_is || 'No summary available.';
      aiAffects.className = 'ai-text';
      aiAffects.textContent = data.how_it_affects || '';
    } else {
      aiWhat.className    = 'ai-error';
      aiWhat.textContent  = 'AI analysis unavailable.';
      aiAffects.textContent = '';
    }

    // Show source link if available
    if (aiSource && event.source_url) {
      aiSource.href        = event.source_url;
      aiSource.textContent = '🔗 Read original source';
      aiSource.style.display = 'inline';
    }
  } catch {
    aiWhat.className    = 'ai-error';
    aiWhat.textContent  = 'Failed to generate AI summary.';
    aiAffects.textContent = '';
  }
}

function closePanel() {
  document.getElementById('side-panel').classList.remove('open');
}

function fillLayer1(ev) {
  const icon = ATTACK_ICONS[ev.attack_type] || '❓';
  document.getElementById('l1-icon').textContent = icon;
  document.getElementById('l1-type').textContent = ev.attack_type || '—';

  const badge = document.getElementById('l1-sev');
  badge.textContent = ev.severity || '—';
  badge.className   = `sev-badge ${(ev.severity || '').toLowerCase()}`;

  const src = ev.source_country || 'Unknown';
  const tgt = ev.target_country || 'Unknown';
  document.getElementById('l1-route').textContent = `${src} → ${tgt}`;
  document.getElementById('l1-age').textContent   = timeAgo(ev.timestamp);
  document.getElementById('l1-desc').textContent  = ev.description || '—';
  
  const meaning = WHAT_THIS_MEANS[ev.attack_type] || WHAT_THIS_MEANS['Unknown'];
  document.getElementById('l1-meaning').innerHTML = `
    <div style="font-size: 13px; font-weight: 600; color: #fff; margin-bottom: 6px;">${meaning.oneliner}</div>
    <div style="margin-bottom: 6px;"><strong>For you:</strong> ${meaning.foryou}</div>
    <div style="color: #aaa;"><strong>High context:</strong> ${meaning.highcon}</div>
  `;

  document.getElementById('cars-badge').textContent = ev.target_country
    ? `Loading CARS for ${ev.target_country}…`
    : '';
}

function fillLayer2(ev) {
  const score = ev.cvss_score;
  const section = document.getElementById('xsev');
  const num   = document.getElementById('cvss-num');
  const fill  = document.getElementById('cvss-fill');

  // Hide entire severity section when no CVSS score available
  if (score == null) {
    if (section) section.style.display = 'none';
    return;
  }

  if (section) section.style.display = '';
  num.textContent        = `${score}/10`;
  fill.style.width       = `${(score / 10) * 100}%`;
  fill.style.background  = score >= 9 ? '#ff3b3b'
                         : score >= 7 ? '#ff7a1a'
                         : score >= 4 ? '#f5c842'
                         :              '#22c97a';
  document.getElementById('cvss-text').textContent = cvssText(score);
}

function fillLayer3(ev) {
  const srcContainer = document.getElementById('l3-src');
  if (ev.source_url) {
    srcContainer.innerHTML = `<a href="${ev.source_url}" target="_blank" class="nvd-link" style="display:inline">🔗 View Primary Source</a>`;
  } else {
    srcContainer.textContent = ev.source_country || 'N/A';
  }
  
  document.getElementById('l3-tgt').textContent  = ev.target_country || 'N/A';
  document.getElementById('l3-feed').textContent = ev.source_feed || 'N/A';

  // CVE row — hide entirely when no CVE ID
  const cveRow = document.getElementById('l3-cve').closest('.df');
  const nvdLink = document.getElementById('l3-nvd');
  if (ev.cve_id) {
    document.getElementById('l3-cve').textContent = ev.cve_id;
    nvdLink.href         = `https://nvd.nist.gov/vuln/detail/${ev.cve_id}`;
    nvdLink.style.display = 'inline';
    if (cveRow) cveRow.style.display = '';
  } else {
    if (cveRow) cveRow.style.display = 'none';
    nvdLink.style.display = 'none';
  }

  // Firecrawl enrichment row — only show if data is present
  const enrichRow = document.getElementById('l3-enrich-row');
  const enrichBox = document.getElementById('l3-enrich');
  if (ev.enriched && ev.enrichment) {
    const enr = typeof ev.enrichment === 'string'
      ? (function() { try { return JSON.parse(ev.enrichment); } catch { return {}; } })()
      : ev.enrichment;
    let content = enr.content || enr.affected_software || JSON.stringify(enr, null, 2);
    if (content.length > 600) content = content.substring(0, 600) + '…';
    enrichBox.textContent = content;
    if (enrichRow) enrichRow.style.display = 'flex';
  } else {
    if (enrichRow) enrichRow.style.display = 'none';
  }

  // Hide entire Advanced section if there's nothing useful to show
  // (no CVE, no enrichment, no source URL — just feed name isn't worth a section)
  const advSection = document.getElementById('xadv');
  const hasAdvData = ev.cve_id || (ev.enriched && ev.enrichment) || ev.source_url;
  if (advSection) advSection.style.display = hasAdvData ? '' : 'none';

  document.getElementById('raw-pre').textContent = JSON.stringify(ev, null, 2);
  document.getElementById('raw-box').classList.remove('vis');
  document.getElementById('raw-btn').textContent = '▶ Raw JSON';
}

async function loadCARS(country) {
  try {
    const resp = await fetch(`${CONFIG.API_URL}/cars/${country}`);
    const data = await resp.json();
    const el   = document.getElementById('cars-badge');
    el.textContent = `${country}: ${data.label} (${data.score})`;
    el.style.color = data.color;
  } catch { /* silent */ }
}

// ── Stats bar + Globe status bar ──────────────────────────────────────────────

let lastIncidentCount = null;

async function updateStats() {
  try {
    const resp = await fetch(`${CONFIG.API_URL}/stats`);
    const d    = await resp.json();
    const total = d.total_today ?? 0;

    // Top stats bar
    document.getElementById('stat-attacks').textContent = total.toLocaleString();
    document.getElementById('stat-target').textContent  = d.top_target      || 'N/A';
    document.getElementById('stat-type').textContent    = d.top_attack_type || 'N/A';
    document.getElementById('stat-updated').textContent = d.last_updated
      ? timeAgo(d.last_updated) : 'Never';

    // Globe status bar — incidents + delta
    const gsInc = document.getElementById('gs-incidents');
    const gsDelta = document.getElementById('gs-delta');
    if (gsInc) gsInc.textContent = total.toLocaleString();
    if (gsDelta && lastIncidentCount !== null) {
      const diff = total - lastIncidentCount;
      if (diff !== 0) {
        const pct = lastIncidentCount > 0 ? ((diff / lastIncidentCount) * 100).toFixed(1) : '0.0';
        gsDelta.textContent = `${diff > 0 ? '+' : ''}${pct}%`;
        gsDelta.className   = `gs-delta ${diff > 0 ? 'negative' : 'positive'}`;
      }
    }
    lastIncidentCount = total;

    // Globe status bar — events/hr estimate
    const gsRate = document.getElementById('gs-rate');
    if (gsRate) gsRate.textContent = d.events_per_hour ?? Math.round(total / 24);
  } catch { /* silent */ }
}

// ── Heatmap ───────────────────────────────────────────────────────────────────

async function fetchHeatmap() {
  try {
    const resp = await fetch(`${CONFIG.API_URL}/heatmap`);
    heatmapData = await resp.json();
    // Rebuild the lookup map for O(1) access in heatmapColor
    heatmapMap = new Map(heatmapData.map(h => [h.country, h]));
    globe.polygonsData([...countryPolygons]);

    // Globe status bar — countries targeted + active CVEs
    const uniqueCountries = new Set(heatmapData.filter(h => h.score > 0).map(h => h.country));
    const gsCo = document.getElementById('gs-countries');
    if (gsCo) gsCo.textContent = uniqueCountries.size;
  } catch { /* silent */ }
}

async function updateGlobeCVEs() {
  try {
    const resp = await fetch(`${CONFIG.API_URL}/events?limit=500`);
    const events = await resp.json();
    const cves = new Set(events.filter(e => e.cve_id).map(e => e.cve_id));
    const gsCves = document.getElementById('gs-cves');
    if (gsCves) gsCves.textContent = cves.size;
  } catch { /* silent */ }
}

// ── Expandable sections ───────────────────────────────────────────────────────

function initExpandables() {
  document.querySelectorAll('.xtoggle').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.xsec').classList.toggle('open');
    });
  });
}

// ── Raw JSON toggle ────────────────────────────────────────────────────────────

function initRawToggle() {
  document.getElementById('raw-btn').addEventListener('click', () => {
    const box = document.getElementById('raw-box');
    const btn = document.getElementById('raw-btn');
    const open = box.classList.toggle('vis');
    btn.textContent = open ? '▼ Raw JSON' : '▶ Raw JSON';
  });
}

// ── Hamburger toggle (responsive) ─────────────────────────────────────────────

function initHamburger() {
  const btn  = document.getElementById('hamburger');
  const feed = document.getElementById('live-feed');
  if (!btn || !feed) return;

  btn.addEventListener('click', () => {
    btn.classList.toggle('active');
    feed.classList.toggle('mobile-open');
  });

  // Close feed panel when clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (feed.classList.contains('mobile-open') &&
        !feed.contains(e.target) &&
        !btn.contains(e.target)) {
      btn.classList.remove('active');
      feed.classList.remove('mobile-open');
    }
  });
}

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initGlobe();
  connectWS();
  startDrip();
  loadStaticNews();
  updateStats();
  fetchHeatmap();
  updateGlobeCVEs();
  setInterval(() => {
    updateStats();
    fetchHeatmap();
    loadStaticNews();
    updateGlobeCVEs();
  }, 60_000);

  // Update timestamps every 30s
  setInterval(() => {
    document.querySelectorAll('#feed-list .fe').forEach(el => {
      const ts = el.dataset.ts;
      if (ts) {
        const ageEl = el.querySelector('.fe-age');
        if (ageEl) ageEl.textContent = timeAgo(ts);
      }
    });
  }, 30_000);

  initExpandables();
  initRawToggle();
  initHamburger();

  document.getElementById('panel-close').addEventListener('click', closePanel);
  const popupClose = document.getElementById('popup-close');
  if (popupClose) popupClose.addEventListener('click', closePopup);
  const popupAction = document.getElementById('popup-action');
  if (popupAction) popupAction.addEventListener('click', () => {
    if (currentPopupEvent) {
      openPanel(currentPopupEvent);
      closePopup();
    }
  });

  // Country overlay close
  const coClose = document.getElementById('co-close');
  if (coClose) coClose.addEventListener('click', closeCountryOverlay);

  document.addEventListener('keydown', e => { 
    if (e.key === 'Escape') {
      closePanel(); 
      closePopup();
      closeCountryOverlay();
      // Also close mobile feed
      const btn  = document.getElementById('hamburger');
      const feed = document.getElementById('live-feed');
      if (btn) btn.classList.remove('active');
      if (feed) feed.classList.remove('mobile-open');
    }
  });
});
