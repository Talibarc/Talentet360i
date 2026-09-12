from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
 
from config import CIS_API_KEY, CIS_API_VERSION, CIS_BASE_URL, CIS_MODEL
 
 
def _get_authorization() -> str:
    key = CIS_API_KEY.strip()
 
    if not key:
        raise RuntimeError("CIS_API_KEY is missing in .env")
 
    if key.lower().startswith("bearer "):
        return key
 
    return f"Bearer {key}"
 
 
def generate_text(system_prompt: str, user_prompt: str) -> str:
    if not CIS_BASE_URL:
        raise RuntimeError("CIS_BASE_URL is missing in .env")
 
    authorization = _get_authorization()
 
    client = ChatCompletionsClient(
        endpoint=CIS_BASE_URL,
        credential=AzureKeyCredential(authorization),
        api_version=CIS_API_VERSION,
    )
 
    try:
        response = client.complete(
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=user_prompt),
            ],
            model=CIS_MODEL,
            headers={"Authorization": authorization},
        )
        return response.choices[0].message.content or ""
    finally:
        client.close()