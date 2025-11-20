"""
Logging configuration for STM Simulator v3.0

Provides centralized logging with both file and console output.
Supports different log levels for development vs production.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# Default log format - includes timestamp, level, module, and message
LOG_FORMAT = (
    '%(asctime)s - %(name)s - %(levelname)s - '
    '[%(filename)s:%(lineno)d] - %(message)s'
)

# Shorter format for console (less verbose)
CONSOLE_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Date format for timestamps
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logger(
    name: str = 'stm_simulator',
    log_dir: Optional[Path] = None,
    log_level: int = logging.INFO,
    console_output: bool = True,
    file_output: bool = True
) -> logging.Logger:
    """
    Set up a logger with file and/or console handlers.
    
    This creates a logger that writes to both a file and the console,
    with configurable formats and levels.
    
    Args:
        name: Logger name (typically module or application name)
        log_dir: Directory to store log files (default: ./logs)
        log_level: Minimum level to log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Whether to output to console
        file_output: Whether to output to file
        
    Returns:
        logging.Logger: Configured logger instance
        
    Example:
        >>> logger = setup_logger('my_module', log_level=logging.DEBUG)
        >>> logger.info("Simulation started")
        >>> logger.warning("High memory usage detected")
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)  # Set minimum level for this logger
    
    # Clear any existing handlers (prevents duplicate logs)
    logger.handlers.clear()
    
    # Console handler - outputs to terminal
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        # Use shorter format for console
        console_formatter = logging.Formatter(CONSOLE_FORMAT, DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler - outputs to log file
    if file_output:
        # Create log directory if it doesn't exist
        if log_dir is None:
            log_dir = Path('./logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp in name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'{name}_{timestamp}.log'
        
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(log_level)
        # Use detailed format for file
        file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Log the log file location
        logger.info(f"Logging to file: {log_file}")
    
    # Prevent propagation to root logger (avoids duplicate logs)
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger by name.
    
    Use this to get a logger that was already set up with setup_logger().
    If the logger doesn't exist, creates a basic one.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Logger instance
        
    Example:
        >>> logger = get_logger('stm_simulator')
        >>> logger.debug("Debug message")
    """
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set up basic console logging
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(CONSOLE_FORMAT, DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


# Convenience function for common logging patterns
class LogContext:
    """
    Context manager for logging the start and end of operations.
    
    Usage:
        with LogContext(logger, "Loading configuration"):
            config = load_config()
        # Automatically logs "Loading configuration - started" and "completed"
    """
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        """
        Initialize the log context.
        
        Args:
            logger: Logger to use
            operation: Description of the operation
            level: Log level to use
        """
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        """Called when entering the 'with' block"""
        self.start_time = datetime.now()
        self.logger.log(self.level, f"{self.operation} - started")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Called when exiting the 'with' block"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            # No exception - operation succeeded
            self.logger.log(
                self.level,
                f"{self.operation} - completed in {elapsed:.2f}s"
            )
        else:
            # Exception occurred - log error
            self.logger.error(
                f"{self.operation} - failed after {elapsed:.2f}s: {exc_val}"
            )
        
        # Return False to propagate exception (if any)
        return False


# Example usage if run as script
if __name__ == '__main__':
    # Set up logger
    logger = setup_logger('test_logger', log_level=logging.DEBUG)
    
    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test context manager
    with LogContext(logger, "Test operation"):
        import time
        time.sleep(1)
        logger.info("Doing work...")
    
    print("\nLog file created in ./logs directory")