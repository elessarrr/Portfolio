# Feature Flag Management System
# This module provides a centralized way to manage feature flags for gradual rollout
# of new functionality. It allows safe deployment of enhanced features while maintaining
# the ability to quickly rollback if issues are discovered.
#
# Key features:
# - Environment variable-based configuration
# - Safe defaults (features disabled by default)
# - Easy integration with existing components
# - Support for different flag types (boolean, string, numeric)
# - Logging and monitoring capabilities

import os
import logging
from typing import Dict, Any, Union, Optional

# Configure logging for this module
logger = logging.getLogger(__name__)

class FeatureFlags:
    """
    Manage feature flags for gradual rollout of new features.
    
    This class provides a centralized way to control feature availability
    through environment variables, allowing for safe deployment and quick
    rollback capabilities.
    
    Features are disabled by default for safety, and must be explicitly
    enabled through environment variables.
    """
    
    def __init__(self):
        """
        Initialize feature flags with default values.
        
        All flags default to False/disabled for safety. They can be enabled
        by setting the corresponding environment variables.
        """
        # Core feature flags for the subpart breakdown enhancement
        self.flags = {
            # Enhanced subpart breakdown with accurate percentages and individual subparts
            'enhanced_subpart_breakdown': self._get_bool_env('ENHANCED_SUBPART_BREAKDOWN', True),
            
            # Debug mode for additional logging and validation
            'debug_mode': self._get_bool_env('DEBUG_MODE', False),
            
            # Validation warnings in UI
            'show_validation_warnings': self._get_bool_env('SHOW_VALIDATION_WARNINGS', True),
            
            # Enhanced tooltips and help text
            'enhanced_tooltips': self._get_bool_env('ENHANCED_TOOLTIPS', True),
            
            # Performance monitoring
            'performance_monitoring': self._get_bool_env('PERFORMANCE_MONITORING', False),
            
            # Data quality checks
            'strict_data_validation': self._get_bool_env('STRICT_DATA_VALIDATION', True),
            
            # Performance optimization features (Phase 1)
            'use_global_data_manager': self._get_bool_env('USE_GLOBAL_DATA_MANAGER', True),
            
            # Performance optimization features (Phase 2)
            'use_smart_cache': self._get_bool_env('USE_SMART_CACHE', True),
            'use_callback_debouncing': self._get_bool_env('USE_CALLBACK_DEBOUNCING', True),
            
            # Performance optimization features (Phase 3)
            'use_pre_aggregation': self._get_bool_env('USE_PRE_AGGREGATION', True)
        }
        
        # Log the current flag states for debugging
        if self.is_enabled('debug_mode'):
            logger.info(f"Feature flags initialized: {self.flags}")
    
    def _get_bool_env(self, env_var: str, default: bool) -> bool:
        """
        Get boolean value from environment variable.
        
        Args:
            env_var: Environment variable name
            default: Default value if environment variable is not set
            
        Returns:
            Boolean value from environment or default
        """
        value = os.getenv(env_var, str(default)).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    def _get_str_env(self, env_var: str, default: str) -> str:
        """
        Get string value from environment variable.
        
        Args:
            env_var: Environment variable name
            default: Default value if environment variable is not set
            
        Returns:
            String value from environment or default
        """
        return os.getenv(env_var, default)
    
    def _get_int_env(self, env_var: str, default: int) -> int:
        """
        Get integer value from environment variable.
        
        Args:
            env_var: Environment variable name
            default: Default value if environment variable is not set
            
        Returns:
            Integer value from environment or default
        """
        try:
            return int(os.getenv(env_var, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {env_var}, using default: {default}")
            return default
    
    def is_enabled(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_name: Name of the feature flag
            
        Returns:
            True if feature is enabled, False otherwise
            
        Raises:
            KeyError: If flag_name is not a valid feature flag
        """
        if flag_name not in self.flags:
            logger.warning(f"Unknown feature flag requested: {flag_name}")
            return False
        
        enabled = self.flags.get(flag_name, False)
        
        # Avoid recursion when checking debug_mode flag
        if flag_name != 'debug_mode' and self.flags.get('debug_mode', False):
            logger.debug(f"Feature flag '{flag_name}' is {'enabled' if enabled else 'disabled'}")
        
        return enabled
    
    def get_flag_value(self, flag_name: str, default: Any = None) -> Any:
        """
        Get the raw value of a feature flag.
        
        Args:
            flag_name: Name of the feature flag
            default: Default value to return if flag doesn't exist
            
        Returns:
            The flag value or default if flag doesn't exist
        """
        return self.flags.get(flag_name, default)
    
    def set_flag(self, flag_name: str, value: Any) -> None:
        """
        Set a feature flag value (for testing purposes).
        
        Args:
            flag_name: Name of the feature flag
            value: Value to set
            
        Note:
            This method is primarily intended for testing. In production,
            flags should be set through environment variables.
        """
        self.flags[flag_name] = value
        
        if self.is_enabled('debug_mode'):
            logger.info(f"Feature flag '{flag_name}' set to: {value}")
    
    def get_all_flags(self) -> Dict[str, Any]:
        """
        Get all feature flags and their current values.
        
        Returns:
            Dictionary of all feature flags and their values
        """
        return self.flags.copy()
    
    def get_enabled_flags(self) -> Dict[str, Any]:
        """
        Get only the enabled feature flags.
        
        Returns:
            Dictionary of enabled feature flags
        """
        return {name: value for name, value in self.flags.items() if value}
    
    def validate_environment(self) -> Dict[str, Any]:
        """
        Validate the current environment configuration.
        
        Returns:
            Dictionary containing validation results and recommendations
        """
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'recommendations': [],
            'enabled_flags': self.get_enabled_flags()
        }
        
        # Check for potentially problematic flag combinations
        if self.is_enabled('enhanced_subpart_breakdown') and not self.is_enabled('strict_data_validation'):
            validation_result['warnings'].append(
                "Enhanced subpart breakdown is enabled but strict data validation is disabled. "
                "Consider enabling strict validation for better data quality."
            )
        
        if self.is_enabled('debug_mode'):
            validation_result['recommendations'].append(
                "Debug mode is enabled. Disable in production for better performance."
            )
        
        if not self.is_enabled('show_validation_warnings'):
            validation_result['warnings'].append(
                "Validation warnings are disabled. Users won't see data quality issues."
            )
        
        # Log validation results if debug mode is enabled
        if self.is_enabled('debug_mode'):
            logger.info(f"Environment validation: {validation_result}")
        
        return validation_result

# Global instance for easy access throughout the application
feature_flags = FeatureFlags()

# Convenience functions for common operations
def is_enhanced_subpart_enabled() -> bool:
    """
    Check if enhanced subpart breakdown is enabled.
    
    Returns:
        True if enhanced subpart breakdown is enabled
    """
    return feature_flags.is_enabled('enhanced_subpart_breakdown')

def is_debug_mode() -> bool:
    """
    Check if debug mode is enabled.
    
    Returns:
        True if debug mode is enabled
    """
    return feature_flags.is_enabled('debug_mode')

def should_show_validation_warnings() -> bool:
    """
    Check if validation warnings should be shown in the UI.
    
    Returns:
        True if validation warnings should be displayed
    """
    return feature_flags.is_enabled('show_validation_warnings')

def get_feature_status() -> Dict[str, Any]:
    """
    Get a summary of all feature flag statuses.
    
    Returns:
        Dictionary with feature flag summary information
    """
    return {
        'all_flags': feature_flags.get_all_flags(),
        'enabled_flags': feature_flags.get_enabled_flags(),
        'validation': feature_flags.validate_environment()
    }

# Environment variable documentation for easy reference
ENVIRONMENT_VARIABLES = {
    'ENHANCED_SUBPART_BREAKDOWN': {
        'description': 'Enable enhanced subpart breakdown with accurate percentages',
        'type': 'boolean',
        'default': 'false',
        'example': 'ENHANCED_SUBPART_BREAKDOWN=true'
    },
    'DEBUG_MODE': {
        'description': 'Enable debug logging and additional validation',
        'type': 'boolean',
        'default': 'false',
        'example': 'DEBUG_MODE=true'
    },
    'SHOW_VALIDATION_WARNINGS': {
        'description': 'Show data validation warnings in the UI',
        'type': 'boolean',
        'default': 'true',
        'example': 'SHOW_VALIDATION_WARNINGS=false'
    },
    'ENHANCED_TOOLTIPS': {
        'description': 'Enable enhanced tooltips and help text',
        'type': 'boolean',
        'default': 'true',
        'example': 'ENHANCED_TOOLTIPS=false'
    },
    'PERFORMANCE_MONITORING': {
        'description': 'Enable performance monitoring and logging',
        'type': 'boolean',
        'default': 'false',
        'example': 'PERFORMANCE_MONITORING=true'
    },
    'STRICT_DATA_VALIDATION': {
        'description': 'Enable strict data validation checks',
        'type': 'boolean',
        'default': 'true',
        'example': 'STRICT_DATA_VALIDATION=false'
    }
}

def print_environment_help():
    """
    Print help information about available environment variables.
    """
    print("\n=== Feature Flag Environment Variables ===")
    print("\nAvailable environment variables for controlling feature flags:\n")
    
    for var_name, info in ENVIRONMENT_VARIABLES.items():
        print(f"{var_name}:")
        print(f"  Description: {info['description']}")
        print(f"  Type: {info['type']}")
        print(f"  Default: {info['default']}")
        print(f"  Example: {info['example']}")
        print()
    
    print("Current status:")
    status = get_feature_status()
    for flag_name, value in status['enabled_flags'].items():
        print(f"  {flag_name}: {value}")
    print()

if __name__ == '__main__':
    # When run directly, print environment help
    print_environment_help()