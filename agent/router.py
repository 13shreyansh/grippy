import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    base_url="https://api.mistral.ai/v1",
    api_key=os.getenv("MISTRAL_API_KEY"),
)

KNOWLEDGE_BASE = {
    "shopee": {
        "company": {
            "name": "Shopee Singapore",
            "method": "email",
            "url": None,
            "email": "support@shopee.sg",
        },
        "regulator": {
            "name": "CASE Singapore",
            "method": "web_form",
            "url": "https://crdcomplaints.azurewebsites.net/",
            "email": "consult@case.org.sg",
        },
    },
    "lazada": {
        "company": {
            "name": "Lazada Singapore",
            "method": "email",
            "url": None,
            "email": "support@lazada.sg",
        },
        "regulator": {
            "name": "CASE Singapore",
            "method": "web_form",
            "url": "https://crdcomplaints.azurewebsites.net/",
            "email": "consult@case.org.sg",
        },
    },
    "grab": {
        "company": {
            "name": "Grab Singapore",
            "method": "email",
            "url": None,
            "email": "support.sg@grab.com",
        },
        "regulator": {
            "name": "CASE Singapore",
            "method": "web_form",
            "url": "https://crdcomplaints.azurewebsites.net/",
            "email": "consult@case.org.sg",
        },
    },
    "singtel": {
        "company": {
            "name": "Singtel",
            "method": "email",
            "url": None,
            "email": "customercare@singtel.com",
        },
        "regulator": {
            "name": "IMDA",
            "method": "email",
            "url": None,
            "email": "info@imda.gov.sg",
        },
    },
    "starhub": {
        "company": {
            "name": "StarHub",
            "method": "email",
            "url": None,
            "email": "customerservice@starhub.com",
        },
        "regulator": {
            "name": "IMDA",
            "method": "email",
            "url": None,
            "email": "info@imda.gov.sg",
        },
    },
    "m1": {
        "company": {
            "name": "M1",
            "method": "email",
            "url": None,
            "email": "customerservice@m1.com.sg",
        },
        "regulator": {
            "name": "IMDA",
            "method": "email",
            "url": None,
            "email": "info@imda.gov.sg",
        },
    },
    "dbs": {
        "company": {
            "name": "DBS Bank",
            "method": "email",
            "url": None,
            "email": "dbsbank@dbs.com",
        },
        "regulator": {
            "name": "MAS",
            "method": "email",
            "url": None,
            "email": "webmaster@mas.gov.sg",
        },
    },
    "ocbc": {
        "company": {
            "name": "OCBC Bank",
            "method": "email",
            "url": None,
            "email": "customer@ocbc.com",
        },
        "regulator": {
            "name": "MAS",
            "method": "email",
            "url": None,
            "email": "webmaster@mas.gov.sg",
        },
    },
    "uob": {
        "company": {
            "name": "UOB Bank",
            "method": "email",
            "url": None,
            "email": "uobgroup@uob.com.sg",
        },
        "regulator": {
            "name": "MAS",
            "method": "email",
            "url": None,
            "email": "webmaster@mas.gov.sg",
        },
    },
    "fairprice": {
        "company": {
            "name": "FairPrice",
            "method": "email",
            "url": None,
            "email": "customerservice@fairprice.com.sg",
        },
        "regulator": {
            "name": "CASE Singapore",
            "method": "web_form",
            "url": "https://crdcomplaints.azurewebsites.net/",
            "email": "consult@case.org.sg",
        },
    },
    "sbs transit": {
        "company": {
            "name": "SBS Transit",
            "method": "email",
            "url": None,
            "email": "feedback@sbstransit.com.sg",
        },
        "regulator": {
            "name": "LTA",
            "method": "email",
            "url": None,
            "email": "feedback@lta.gov.sg",
        },
    },
    "smrt": {
        "company": {
            "name": "SMRT",
            "method": "email",
            "url": None,
            "email": "feedback@smrt.com.sg",
        },
        "regulator": {
            "name": "LTA",
            "method": "email",
            "url": None,
            "email": "feedback@lta.gov.sg",
        },
    },
}

DEFAULT_ROUTING = {
    "company": {
        "name": "Unknown Company",
        "method": "email",
        "url": None,
        "email": "",
    },
    "regulator": {
        "name": "CASE Singapore",
        "method": "web_form",
        "url": "https://crdcomplaints.azurewebsites.net/",
        "email": "consult@case.org.sg",
    },
}


def _extract_json(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(text[start:end])
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


async def route_complaint(complaint_data: dict) -> dict:
    company_name = str(complaint_data.get("complaint_company", "")).lower().strip()

    for key, routing in KNOWLEDGE_BASE.items():
        if key in company_name or company_name in key:
            logger.info("Matched '%s' to knowledge base entry '%s'", company_name, key)
            return routing

    logger.info("Company '%s' not in knowledge base, using Mistral", company_name)
    try:
        response = await client.chat.completions.create(
            model="mistral-large-2411",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a complaint routing engine for Singapore. "
                        "Return ONLY valid JSON with this exact shape: "
                        "{\"company\":{\"name\":\"...\",\"method\":\"email\",\"url\":null,\"email\":\"...\"},"
                        "\"regulator\":{\"name\":\"CASE Singapore\",\"method\":\"web_form\","
                        "\"url\":\"https://crdcomplaints.azurewebsites.net/\",\"email\":\"consult@case.org.sg\"}}. "
                        "Use company method email by default."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Route complaint for company: {complaint_data.get('complaint_company', 'Unknown')}",
                },
            ],
            temperature=0.1,
        )
        parsed = _extract_json(response.choices[0].message.content.strip())
        if parsed:
            return parsed
    except Exception as error:
        logger.error("Mistral routing failed: %s", error)

    return DEFAULT_ROUTING
