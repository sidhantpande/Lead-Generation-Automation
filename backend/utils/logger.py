import sys
from pathlib import Path
from loguru import logger

# Ensure logs directory exists
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOGS_DIR / "pipeline.log"

# Configure Loguru
logger.remove()  # Remove default handler

# Add console handler with customized format
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    enqueue=True
)

# Add file handler for detailed logs
logger.add(
    str(log_file),
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    enqueue=True
)

# Expose a pipeline-specific logger utility
def log_step(step_number: int, stage_name: str, message: str, status: str = "INFO"):
    log_msg = f"[STEP {step_number}] [{stage_name}] {message}"
    if status == "SUCCESS":
        logger.success(log_msg)
    elif status == "WARNING":
        logger.warning(log_msg)
    elif status == "ERROR":
        logger.error(log_msg)
    else:
        logger.info(log_msg)
