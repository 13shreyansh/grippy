import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

response = requests.post(
    "https://agent.tinyfish.ai/v1/automation/run-sse",
    headers={
        "X-API-Key": os.environ["TINYFISH_API_KEY"],
        "Content-Type": "application/json"
    },
    json={
        "url": "https://ecaseline.case.org.sg",
        "goal": "Navigate to https://ecaseline.case.org.sg. Find a button or link that says File a Complaint or Lodge a Complaint or Submit Complaint. Click it. Tell me what you see on the next page — specifically: is there a form visible without needing to log in or create an account? What fields are on the form? Return the result as JSON: {\"status\": \"success\", \"login_required\": true or false, \"form_fields_visible\": [\"list of field labels you can see\"]}"
    },
    stream=True
 )

for line in response.iter_lines():
    if line:
        decoded = line.decode()
        if decoded.startswith("data: "):
            try:
                event = json.loads(decoded[6:])
                print(f"EVENT TYPE: {event.get('type')} | DATA: {json.dumps(event)[:300]}")
            except:
                print(decoded)
