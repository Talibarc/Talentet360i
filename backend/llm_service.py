from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
 
from luna_contract import invalid, structural_log

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
        choices = getattr(response, "choices", None)
        structural_log("response_received", {"choices": choices},
                       choice_count=len(choices) if isinstance(choices, list) else None)
        if not isinstance(choices, list) or len(choices) != 1:
            invalid(None, "expected_one_choice")
        choice = choices[0]
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if (getattr(choice, "finish_reason", None) not in (None, "stop")
                or getattr(message, "role", None) not in (None, "assistant")
                or getattr(message, "tool_calls", None) or getattr(message, "refusal", None)
                or not isinstance(content, str)):
            invalid(None, "expected_completed_text_message")
        return content
    finally:
        client.close()