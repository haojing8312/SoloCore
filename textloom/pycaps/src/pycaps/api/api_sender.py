import uuid
import requests
from requests.exceptions import Timeout, RequestException
from .api_key_service import ApiKeyService
from time import sleep
from pycaps.logger import logger

_PYCAPS_API_URL = "http://pycaps.com/api/process"
_MAX_RETRIES = 3
_SESSION_ID = None

def start() -> None:
    global _SESSION_ID

    _SESSION_ID = str(uuid.uuid4())

def send(feature_id: str, payload: dict) -> dict:
    if not _SESSION_ID:
        raise RuntimeError("Session id not set, start() should be called first.")
    
    body = {
        "api_key": ApiKeyService.get(),
        "rendering_id": _SESSION_ID,
        "feature": feature_id,
        "payload": payload
    }
    
    retries = 0
    while retries < _MAX_RETRIES:
        try:
            response = requests.post(_PYCAPS_API_URL, json=body)
            
            if 200 <= response.status_code < 300:
                return response.json()
            elif 400 <= response.status_code < 500:
                raise RequestException(f"Client error: {response.status_code} - {response.text}")
            else:
                retries += 1
                if retries == _MAX_RETRIES:
                    raise RequestException(f"Server error after {_MAX_RETRIES} retries: {response.status_code} - {response.text}")
                
        except Timeout:
            retries += 1
            if retries == _MAX_RETRIES:
                raise Timeout(f"Request timed out after {_MAX_RETRIES} retries")
        
        logger().debug(f"Pycaps API error... trying again request again (response code: {response.status_code} | response text: {response.text})")
        sleep(2)

def close() -> None:
    global _SESSION_ID

    _SESSION_ID = None
