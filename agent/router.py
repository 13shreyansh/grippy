import os
import json
import logging
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    base_url="https://api.mistral.ai/v1",
    api_key=os.getenv("MISTRAL_API_KEY" )
)

KNOWLEDGE_BASE = {
    "shopee": {
        "company": {"name": "Shopee Singapore", "method": "email", "url": None, "email": "support@shopee.sg"},
        "regulator": {"name": "CASE Singapore", "method": "web_form", "url": "https://crdcomplaints.azurewebsites.net/", "email": "consult@case.org.sg"}
    },
    "lazada": {
        "company": {"name": "Lazada Singapore", "method": "email", "url": None, "email": "support@lazada.sg"},
        "regulator": {"name": "CASE Singapore", "method": "web_form", "url": "https://crdcomplaints.azurewebsites.net/", "email": "consult@case.org.sg"}
    },
    "grab": {
        "company": {"name": "Grab Singapore", "method": "email", "url": None, "email": "support.sg@grab.com"},
        "regulator": {"name": "CASE Singapore", "method": "web_form", "url": "https://crdcomplaints.azurewebsites.net/", "email": "consult@case.org.sg"}
    },
    "singtel": {
        "company": {"name": "Singtel", "method": "web_form", "url": "https://www.singtel.com/contact-us", "email": "customercare@singtel.com"},
        "regulator": {"name": "IMDA", "method": "web_form", "url": "https://www.imda.gov.sg/contact-us", "email": "info@imda.gov.sg"}
    },
    "starhub": {
        "company": {"name": "StarHub", "method": "web_form", "url": "https://www.starhub.com/contact-us", "email": "customerservice@starhub.com"},
        "regulator": {"name": "IMDA", "method": "web_form", "url": "https://www.imda.gov.sg/contact-us", "email": "info@imda.gov.sg"}
    },
    "m1": {
        "company": {"name": "M1", "method": "email", "url": None, "email": "customerservice@m1.com.sg"},
        "regulator": {"name": "IMDA", "method": "web_form", "url": "https://www.imda.gov.sg/contact-us", "email": "info@imda.gov.sg"}
    },
    "dbs": {
        "company": {"name": "DBS Bank", "method": "web_form", "url": "https://www.dbs.com.sg/personal/support/contact-us", "email": "dbsbank@dbs.com"},
        "regulator": {"name": "MAS", "method": "web_form", "url": "https://www.mas.gov.sg/consumerfeedback-form/", "email": "webmaster@mas.gov.sg"}
    },
    "ocbc": {
        "company": {"name": "OCBC Bank", "method": "email", "url": None, "email": "customer@ocbc.com"},
        "regulator": {"name": "MAS", "method": "web_form", "url": "https://www.mas.gov.sg/consumerfeedback-form/", "email": "webmaster@mas.gov.sg"}
    },
    "uob": {
        "company": {"name": "UOB Bank", "method": "email", "url": None, "email": "uobgroup@uob.com.sg"},
        "regulator": {"name": "MAS", "method": "web_form", "url": "https://www.mas.gov.sg/consumerfeedback-form/", "email": "webmaster@mas.gov.sg"}
    },
    "fairprice": {
        "company": {"name": "FairPrice", "method": "email", "url": None, "email": "customerservice@fairprice.com.sg"},
        "regulator": {"name": "CASE Singapore", "method": "web_form", "url": "https://crdcomplaints.azurewebsites.net/", "email": "consult@case.org.sg"}
    },
    "sbs transit": {
        "company": {"name": "SBS Transit", "method": "web_form", "url": "https://www.sbstransit.com.sg/feedback", "email": "feedback@sbstransit.com.sg"},
        "regulator": {"name": "LTA", "method": "email", "url": None, "email": "feedback@lta.gov.sg"}
    },
    "smrt": {
        "company": {"name": "SMRT", "method": "web_form", "url": "https://www.smrt.com.sg/feedback", "email": "feedback@smrt.com.sg"},
        "regulator": {"name": "LTA", "method": "email", "url": None, "email": "feedback@lta.gov.sg"}
    }
}

DEFAULT_ROUTING = {
    "company": {"name": "Unknown Company", "method": "email", "url": None, "email": ""},
    "regulator": {"name": "CASE Singapore", "method": "web_form", "url": "https://crdcomplaints.azurewebsites.net/", "email": "consult@case.org.sg"}
}

async def route_complaint(complaint_data: dict ) -> dict:
    company_name = complaint_data.get("complaint_company", "").lower().strip()
    
    # Check knowledge base first
    for key, routing in KNOWLEDGE_BASE.items():
        if key in company_name or company_name in key:
            logger.info(f"Matched '{company_name}' to knowledge base entry '{key}'")
            return routing
    
    # Fall back to Mistral for unknown companies
    logger.info(f"Company '{company_name}' not in knowledge base, using Mistral")
    try:
        response = await client.chat.completions.create(
            model="mistral-large-2411",
            messages=[
                {
                    "role": "system",
                    "content": """You are a complaint routing engine for Singapore. Given a company name, return a JSON routing decision.
Return ONLY valid JSON, no other text:
{
  "company": {"name": "official company name", "method": "email", "url": null, "email": "support@company.com.sg"},
  "regulator": {"name": "CASE Singapore", "method": "web_form", "url": "https://crdcomplaints.azurewebsites.net/", "email": "consult@case.org.sg"}
}
Default method to "email". Default regulator to CASE Singapore."""
                },
                {
                    "role": "user",
                    "content": f"Route complaint for company: {complaint_data.get('complaint_company', 'Unknown' )}"
                }
            ],
            temperature=0.1
        )
        text = response.choices[0].message.content.strip()
        # Extract JSON from response
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        logger.error(f"Mistral routing failed: {e}")
    
    return DEFAULT_ROUTING
