from pycaps.common import ConfigService

class ApiKeyService:

    API_KEY_CONFIG_KEY = "api_key"

    @staticmethod
    def get() -> str:
        return ConfigService.get(ApiKeyService.API_KEY_CONFIG_KEY)
    
    @staticmethod
    def set(api_key: str) -> None:
        ConfigService.set(ApiKeyService.API_KEY_CONFIG_KEY, api_key)

    @staticmethod
    def has() -> bool:
        return ConfigService.has(ApiKeyService.API_KEY_CONFIG_KEY)

    @staticmethod
    def remove() -> bool:
        ConfigService.remove(ApiKeyService.API_KEY_CONFIG_KEY)
