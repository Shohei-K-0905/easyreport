import json
import webbrowser
import os
from playsound import playsound
from config import settings
from db import SessionLocal
from models import Notification, TPEntry, FormSubmission
# from .ms_teams import send_teams_message
from openpyxl import load_workbook
import logging
from logging import getLogger

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

def notify_before(schedule_id: int, message: str):
    """
    Send a reminder notification via Teams and record it.
    """
    logger.info(f"Executing notify_before job for schedule_id: {schedule_id} with message: '{message}'")
    # send_teams_message(message)
    session = SessionLocal()
    session.add(Notification(schedule_id=schedule_id, channel_type="teams", message=message))
    session.commit()
    session.close()


def open_resources():
    """
    Open the Excel file and Google Form in the web browser for manual input.
    """
    file_path = getattr(settings, "EXCEL_FILE_PATH", None)
    if file_path:
        webbrowser.open(f"file://{os.path.abspath(file_path)}")
    form_id = getattr(settings, "GOOGLE_FORM_ID", None)
    if form_id:
        webbrowser.open(f"https://docs.google.com/forms/d/e/{form_id}/viewform")


def play_alert_sound():
    """Plays an alert sound."""
    # IMPORTANT: Place an 'alert.wav' file in the project's 'src' directory
    # or update the path accordingly.
    sound_file = os.path.join(os.path.dirname(__file__), 'alert.wav')
    try:
        logger.info("Attempting to play alert sound...")
        playsound(sound_file)
        logger.info("Alert sound played.")
    except Exception as e:
        # Handle cases where playsound fails (e.g., file not found, platform issues)
        logger.error(f"Could not play sound file '{sound_file}': {e}")
        # Consider adding a fallback mechanism or just logging the error.


def open_google_form():
    """Opens the Google Form in the default web browser."""
    if not settings.GOOGLE_FORM_ID:
        logger.error("GOOGLE_FORM_ID is not set in the environment variables.")
        return

    # Construct the viewform URL
    form_url = f"https://docs.google.com/forms/d/e/{settings.GOOGLE_FORM_ID}/viewform"
    try:
        logger.info(f"Opening Google Form URL: {form_url}")
        webbrowser.open(form_url, new=2) # new=2 opens in a new tab, if possible
        logger.info("Google Form opened successfully.")
    except Exception as e:
        logger.error(f"Could not open web browser for URL '{form_url}': {e}")


def report_job(schedule_id: int, prompts: list[str]):
    """
    Orchestrate full reporting workflow: voice dialog, Excel update, Google Form submission.
    """
    # responses = run_voice_dialog(schedule_id, prompts)
    logger.warning("run_voice_dialog is currently disabled.") # Placeholder log
    # submit_google_form(responses)
    logger.warning("submit_google_form is currently disabled.") # Placeholder log
    logger.info(f"Report job for schedule_id {schedule_id} completed (Placeholder).")


def voice_dialog_job(schedule_id: int, prompts: list[str]) -> dict[str, str]:
    """
    Run the voice dialog and return recognized responses.
    """
    # return run_voice_dialog(schedule_id, prompts)
    logger.warning("run_voice_dialog is currently disabled.") # Placeholder log
    return {}
