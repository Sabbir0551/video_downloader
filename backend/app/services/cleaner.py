import sys
import time
import logging
from app.core.config import settings
from app.worker.tasks import clean_expired_downloads_task

logger = logging.getLogger("anystream.janitor")

def run_janitor_loop(run_once: bool = False):
    """Runs the janitor eviction task periodically or once."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("Starting AnyStream Janitor Service (interval=%ss)...", settings.FILE_CLEANUP_INTERVAL_SECONDS)
    
    while True:
        try:
            logger.info("Running janitor cleanup sweep...")
            result = clean_expired_downloads_task()
            logger.info("Janitor sweep completed: %s", result)
        except Exception as exc:
            logger.error("Janitor execution failed: %s", exc, exc_info=True)
            
        if run_once:
            break
            
        time.sleep(settings.FILE_CLEANUP_INTERVAL_SECONDS)

if __name__ == "__main__":
    once = "--once" in sys.argv
    run_janitor_loop(run_once=once)
