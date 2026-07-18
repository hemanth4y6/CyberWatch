import os
import json
import logging
from httpx import AsyncClient

logger = logging.getLogger(__name__)

async def generate_ai_briefing(news_events: list[dict]) -> str:
    """Takes a list of top events and generates a short 1-2 sentence daily briefing using Groq."""
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "AI Briefing unavailable. GROQ_API_KEY not configured."
        
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    
    try:
        context_items = []
        for e in news_events[:8]:
            context_items.append(f"- {e.get('attack_type', 'Threat')}: {e.get('description', '')}")
            
        context_str = "\n".join(context_items)
        
        prompt = (
            "You are a cybersecurity analyst generating a very short, punchy Daily Briefing widget. "
            "Write exactly 2-3 short sentences summarizing the overall theme of these top cyber threats today. "
            "Do not use markdown formatting. Be authoritative and concise.\n\n"
            f"Top Threats:\n{context_str}\n\nBriefing:"
        )

        async with AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 80
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"Groq API error: {resp.text}")
                return "AI Briefing generation failed."
                
    except Exception as e:
        logger.error(f"Error generating Groq briefing: {e}")
        return "AI Briefing generation encountered an error."


async def generate_event_summary(event_data: dict) -> dict:
    """Generates a structured AI analysis for a single security event using Groq."""
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"what_it_is": "AI analysis unavailable — GROQ_API_KEY not set.", "how_it_affects": ""}

    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    title       = event_data.get("title", "Unknown incident")
    attack_type = event_data.get("attack_type", "Unknown")
    severity    = event_data.get("severity", "Unknown")
    src         = event_data.get("source_country") or "global"
    tgt         = event_data.get("target_country") or "global"
    cve         = event_data.get("cve_id")
    cve_line    = f" CVE: {cve}." if cve else ""

    # Use a system prompt for strict JSON output without using response_format (broader model support)
    system_msg = (
        'You are a cybersecurity analyst API. You MUST respond with ONLY a JSON object. '
        'No preamble, no markdown, no explanation. Just raw JSON.'
    )
    user_msg = (
        f'Incident: "{title}"\n'
        f'Type: {attack_type} | Severity: {severity} | Origin: {src} \u2192 Target: {tgt}{cve_line}\n'
        f'Return exactly: {{"what_it_is": "<2 sentences: what happened, no jargon>", '
        f'"how_it_affects": "<2 sentences: impact on regular users or organisations>"}}'  
    )

    try:
        async with AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user",   "content": user_msg}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 220,
                }
            )
            if resp.status_code != 200:
                logger.error(f"Groq event summary error {resp.status_code}: {resp.text}")
                return {"what_it_is": "AI analysis temporarily unavailable.", "how_it_affects": ""}

            text = resp.json()["choices"][0]["message"]["content"].strip()

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            # Try JSON parse
            try:
                parsed = json.loads(text)
                return {
                    "what_it_is":    parsed.get("what_it_is", "").strip(),
                    "how_it_affects": parsed.get("how_it_affects", "").strip()
                }
            except Exception:
                logger.warning(f"Groq non-JSON response, returning raw: {text[:100]}")
                return {"what_it_is": text, "how_it_affects": ""}

    except Exception as e:
        logger.error(f"Groq event summary exception: {e}")
        return {"what_it_is": "AI analysis encountered an error.", "how_it_affects": ""}
