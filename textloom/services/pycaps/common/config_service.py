import os
import json

class ConfigService:

    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".pycaps")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
    _cache: dict = None

    @staticmethod
    def get(config_key: str) -> str:
        return ConfigService.get_all()[config_key]

    @staticmethod
    def get_all() -> dict:
        if ConfigService._cache:
            return ConfigService._cache
        
        if not os.path.exists(ConfigService.CONFIG_FILE):
            ConfigService._cache = {}
            return ConfigService._cache

        with open(ConfigService.CONFIG_FILE, "r", encoding="utf-8") as f:
            ConfigService._cache = json.load(f)
    
        return ConfigService._cache
    
    @staticmethod
    def set(config_key: str, value) -> None:
        config = ConfigService.get_all()
        config[config_key] = value
        ConfigService.set_all(config)

    @staticmethod
    def set_all(config: dict) -> None:
        os.makedirs(ConfigService.CONFIG_DIR, exist_ok=True)
        with open(ConfigService.CONFIG_FILE, "w") as f:
            json.dump(config, f)

        ConfigService._cache = config

    @staticmethod
    def has(config_key: str) -> bool:
        return config_key in ConfigService.get_all()

    @staticmethod
    def remove(config_key: str) -> bool:
        config = ConfigService.get_all()
        del config[config_key]
        ConfigService.set_all(config)
