"""
Structured Logging Configuration

This module provides JSON-style structured logging for the application.
Includes timestamps, level, route information, and other contextual data.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any
from config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON objects.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "route"):
            log_data["route"] = record.route
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = record.ip_address
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """
    Standard text formatter with structured output.
    """
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging(
    level: Optional[str] = None,
    format_type: Optional[str] = None
) -> logging.Logger:
    """
    Configure and return the root logger for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("json" or "text")
        
    Returns:
        Configured logger instance
    """
    log_level = level or settings.LOG_LEVEL
    log_format = format_type or settings.LOG_FORMAT
    
    # Get the root logger
    logger = logging.getLogger("intelliweather")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Set formatter based on format type
    if log_format.lower() == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(TextFormatter())
    
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Name for the logger (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"intelliweather.{name}")


class LogContext:
    """
    Context manager for adding extra context to log records.
    """
    
    def __init__(self, logger: logging.Logger, **kwargs):
        self.logger = logger
        self.extra = kwargs
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def info(self, message: str, **kwargs):
        """Log an info message with context."""
        extra = {**self.extra, **kwargs}
        self.logger.info(message, extra={"extra_data": extra})
        
    def error(self, message: str, **kwargs):
        """Log an error message with context."""
        extra = {**self.extra, **kwargs}
        self.logger.error(message, extra={"extra_data": extra})
        
    def warning(self, message: str, **kwargs):
        """Log a warning message with context."""
        extra = {**self.extra, **kwargs}
        self.logger.warning(message, extra={"extra_data": extra})
        
    def debug(self, message: str, **kwargs):
        """Log a debug message with context."""
        extra = {**self.extra, **kwargs}
        self.logger.debug(message, extra={"extra_data": extra})


# Initialize the logger on module import
logger = setup_logging()
