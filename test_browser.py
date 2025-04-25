# /Users/kusabirakishohei/Desktop/easyreport/test_browser.py
import webbrowser
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# ここにご自身のGoogle FormのURLを貼り付けてください
test_url = "https://docs.google.com/forms/d/e/1FAIpQLSfOx4GvXvEzTkLtbRP-M3NDHPFumkgWuTjppz8ZWKWjekMmlw/viewform?usp=header"

logger.info(f"Attempting to open URL: {test_url}")
try:
    opened = webbrowser.open(test_url)
    if opened:
        logger.info(f"webbrowser.open reported success for URL: {test_url}")
    else:
        logger.warning(f"webbrowser.open reported failure for URL: {test_url}")
except Exception as e:
    logger.error(f"An error occurred while trying to open the URL: {e}", exc_info=True)
