"""Configuration loader for the Perp DEX Discord Bot."""

import os
import re
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


class ConfigLoader:
    """Configuration loader with environment variable expansion and validation."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the config loader.

        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = config_path
        self._config: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Dict[str, Any]: Loaded and processed configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
            ValueError: If required environment variables are missing
        """
        # Load environment variables from .env file
        load_dotenv()

        # Check if config file exists
        if not Path(self.config_path).exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        # Load YAML
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Expand environment variables
        config = self._expand_env_vars(config)

        # Validate configuration
        self._validate_config(config)

        self._config = config
        logger.info(f"Configuration loaded successfully from {self.config_path}")
        return config

    def _expand_env_vars(self, obj: Any) -> Any:
        """
        Recursively expand environment variables in configuration.

        Supports ${VAR_NAME} syntax.

        Args:
            obj: Configuration object (dict, list, str, etc.)

        Returns:
            Any: Configuration with environment variables expanded

        Raises:
            ValueError: If required environment variable is not set
        """
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Find all ${VAR_NAME} patterns
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, obj)

            for var_name in matches:
                env_value = os.getenv(var_name)
                if env_value is None:
                    raise ValueError(
                        f"Environment variable '{var_name}' is not set. "
                        f"Please set it in your .env file or environment."
                    )
                obj = obj.replace(f'${{{var_name}}}', env_value)

            return obj
        else:
            return obj

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration structure and required fields.

        Args:
            config: Configuration dictionary

        Raises:
            ValueError: If configuration is invalid
        """
        # Check top-level sections
        required_sections = ['schedule', 'exchanges', 'analysis', 'discord', 'storage', 'logging']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required section in config: '{section}'")

        # Validate exchanges
        if not config['exchanges']:
            raise ValueError("No exchanges configured")

        for exchange in config['exchanges']:
            required_fields = ['name', 'type', 'enabled', 'api_base_url']
            for field in required_fields:
                if field not in exchange:
                    raise ValueError(f"Exchange missing required field: '{field}'")

        # Validate schedule
        schedule = config['schedule']
        if 'common_pairs_update' not in schedule:
            raise ValueError("Schedule missing 'common_pairs_update'")
        if 'notification_time' not in schedule:
            raise ValueError("Schedule missing 'notification_time'")

        # Validate analysis parameters
        analysis = config['analysis']
        if 'fr_divergence' not in analysis:
            raise ValueError("Analysis missing 'fr_divergence' section")
        if 'oi_ratio' not in analysis:
            raise ValueError("Analysis missing 'oi_ratio' section")

        # Validate Discord webhook URL
        discord = config['discord']
        if 'webhook_url' not in discord:
            raise ValueError("Discord section missing 'webhook_url'")

        webhook_url = discord['webhook_url']
        if not webhook_url or webhook_url.strip() == '':
            raise ValueError("Discord webhook_url is empty")
        if not webhook_url.startswith('https://discord.com/api/webhooks/'):
            logger.warning(f"Discord webhook URL format may be invalid: {webhook_url}")

        # Validate storage
        storage = config['storage']
        if 'cache_file' not in storage:
            raise ValueError("Storage section missing 'cache_file'")

        # Validate logging
        logging_config = config['logging']
        if 'level' not in logging_config:
            raise ValueError("Logging section missing 'level'")
        if 'file' not in logging_config:
            raise ValueError("Logging section missing 'file'")

        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if logging_config['level'] not in valid_log_levels:
            raise ValueError(
                f"Invalid log level: '{logging_config['level']}'. "
                f"Valid levels: {', '.join(valid_log_levels)}"
            )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key (supports dot notation, e.g., 'discord.webhook_url')
            default: Default value if key not found

        Returns:
            Any: Configuration value
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")

        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_enabled_exchanges(self) -> list:
        """
        Get list of enabled exchange configurations.

        Returns:
            list: List of enabled exchange configurations
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")

        return [ex for ex in self._config['exchanges'] if ex.get('enabled', False)]


# Test function
def _test_config_loader():
    """Test function for ConfigLoader."""
    print("Testing ConfigLoader...")

    # Set test environment variable
    os.environ['DISCORD_WEBHOOK_URL'] = 'https://discord.com/api/webhooks/test/token'

    loader = ConfigLoader('config.yaml')

    try:
        config = loader.load()
        print("✓ Configuration loaded successfully")

        # Test get method
        webhook_url = loader.get('discord.webhook_url')
        print(f"✓ Discord webhook URL: {webhook_url}")

        # Test enabled exchanges
        enabled_exchanges = loader.get_enabled_exchanges()
        print(f"✓ Enabled exchanges: {[ex['name'] for ex in enabled_exchanges]}")

        # Test dot notation
        log_level = loader.get('logging.level')
        print(f"✓ Log level: {log_level}")

        # Test default value
        missing = loader.get('nonexistent.key', 'default_value')
        print(f"✓ Default value works: {missing}")

        # Display some config values
        print("\nConfiguration summary:")
        print(f"  Schedule notification time: {config['schedule']['notification_time']}")
        print(f"  FR divergence min volume: ${config['analysis']['fr_divergence']['min_volume_usd']:,}")
        print(f"  OI ratio top N: {config['analysis']['oi_ratio']['top_n']}")
        print(f"  Cache file: {config['storage']['cache_file']}")

        print("\n✓ All tests passed!")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    _test_config_loader()
