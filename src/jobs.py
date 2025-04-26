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
import subprocess
import sys
import platform
import dotenv

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


def open_google_form(url: str):
    """Opens the provided URL in the default web browser using OS-specific commands."""
    logger.info(f"--- Entering open_google_form ---")
    logger.info(f"Received URL argument: {url}")

    if not url:
        logger.warning("No URL provided to open_google_form, skipping.")
        return

    logger.info(f"Attempting to open URL: {url}")
    system = platform.system()
    try:
        if system == "Darwin": # macOS
            logger.info("Detected macOS. Using 'open' command.")
            result = subprocess.run(['open', url], check=True, capture_output=True, text=True)
            logger.info(f"'open {url}' command executed.")
        elif system == "Windows":
            logger.info("Detected Windows. Using 'start' command.")
            # 'start' needs shell=True on Windows
            result = subprocess.run(['start', url], shell=True, check=True, capture_output=True, text=True)
            logger.info(f"'start {url}' command executed.")
        else: # Other OS (Linux, etc.)
            logger.info(f"Detected {system}. Falling back to webbrowser.open.")
            opened = webbrowser.open(url)
            if opened:
                logger.info(f"webbrowser.open reported success for URL: {url}")
            else:
                # This fallback might not work reliably from background threads
                logger.warning(f"webbrowser.open reported failure for URL: {url}. This might be expected in background jobs on {system}.")

    except FileNotFoundError:
        command = "open" if system == "Darwin" else "start" if system == "Windows" else "webbrowser"
        logger.error(f"Command '{command}' not found or webbrowser unavailable.")
    except subprocess.CalledProcessError as e:
        command = "open" if system == "Darwin" else "start"
        logger.error(f"'{command} {url}' command failed with error code {e.returncode}: {e.stderr}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while trying to open the URL: {e}", exc_info=True)


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


def open_local_file(filename_from_db: str):
    """指定されたファイルパスが絶対パスの場合はそのまま、相対パスの場合は環境変数のベースパスを元に開く"""

    if not filename_from_db:
        logger.warning("No Excel filename provided for this schedule. Skipping file open.")
        return

    # Check if the path from DB is already absolute
    if os.path.isabs(filename_from_db):
        absolute_file_path = filename_from_db
        logger.info(f"Using absolute path from database: {absolute_file_path}")
    else:
        # Path is relative, use EXCEL_BASE_PATH from .env
        base_path = os.getenv('EXCEL_BASE_PATH')
        if not base_path:
            logger.error("Error: EXCEL_BASE_PATH environment variable is not set in .env file for relative path.")
            return
        absolute_file_path = os.path.join(base_path, filename_from_db)
        logger.info(f"Using relative path from database, joined with base path: {absolute_file_path}")

    logger.info(f"Attempting to open file: {absolute_file_path}")

    if not os.path.exists(absolute_file_path):
        logger.error(f"Error: File path '{absolute_file_path}' is invalid or does not exist.")
        return

    try:
        system = platform.system()
        if system == "Windows":
            # os.startfile(absolute_file_path) # 代替案
            subprocess.run(['start', '', absolute_file_path], check=True, shell=True)
        elif system == "Darwin":  # macOS
            subprocess.run(['open', absolute_file_path], check=True)
        else:  # Linuxなど
            subprocess.run(['xdg-open', absolute_file_path], check=True)
        logger.info(f"Opened file: {absolute_file_path}")
    except FileNotFoundError:
        logger.error(f"Error: The file '{absolute_file_path}' was not found.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error opening file '{absolute_file_path}': {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while opening file '{absolute_file_path}': {e}")
