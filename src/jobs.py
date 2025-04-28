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
import requests

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


def play_alert_sound(schedule_id: int):
    """Plays the alert sound relative to this script's location and notifies the main app."""
    sound_filename = "alert.wav"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sound_file_path = os.path.join(script_dir, sound_filename)

    logger.info(f"Attempting to play alert sound for schedule {schedule_id} from: {sound_file_path}")
    try:
        if not os.path.exists(sound_file_path):
            logger.error(f"Alert sound file not found at {sound_file_path}")
            # Still attempt to notify the app even if sound fails
        else:
            if platform.system() == "Darwin":  # macOS
                logger.info(f"Using 'afplay' on macOS for path: {sound_file_path}")
                result = subprocess.run(['afplay', sound_file_path], check=False, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"'afplay' completed successfully for schedule {schedule_id}.")
                else:
                    logger.error(f"'afplay' failed for schedule {schedule_id} with code {result.returncode}. Error: {result.stderr}")
            else:  # Fallback for other systems
                logger.info(f"Using 'playsound' for schedule {schedule_id} with path: {sound_file_path}")
                playsound(sound_file_path)
                logger.info(f"'playsound' call completed for schedule {schedule_id}.")

    except Exception as e:
        logger.error(f"Failed to play alert sound '{sound_file_path}' for schedule {schedule_id}: {e}", exc_info=True)
        # Continue to notification even if sound playback fails

    # Notify the Flask app that the alert was triggered
    try:
        # Assuming Flask app runs on localhost:5001 (adjust if different)
        # TODO: Make the base URL configurable
        notify_url = f"http://127.0.0.1:5001/internal/notify_alert/{schedule_id}"
        response = requests.post(notify_url, timeout=5) # Send POST request
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        logger.info(f"Successfully notified Flask app about alert for schedule {schedule_id}.")
    except requests.exceptions.RequestException as notify_err:
        logger.error(f"Failed to notify Flask app about alert for schedule {schedule_id}: {notify_err}")


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
        cmd = []
        if system == "Windows":
            # Use start command which doesn't block and handles spaces better via the first empty arg
            cmd = ['start', '', absolute_file_path]
            # Using shell=True might be necessary for 'start' on some Windows setups
            result = subprocess.run(cmd, check=False, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace') # Use shell=True for start, capture output
        elif system == "Darwin":  # macOS
            cmd = ['open', absolute_file_path]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True, encoding='utf-8', errors='replace') # check=False to capture error
        else:  # Linuxなど
            cmd = ['xdg-open', absolute_file_path]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True, encoding='utf-8', errors='replace') # check=False to capture error

        # Check return code and stderr
        if result.returncode != 0:
            error_message = f"Error opening file '{absolute_file_path}' with command '{' '.join(cmd)}'. Return code: {result.returncode}."
            stderr_output = result.stderr.strip()
            if stderr_output:
                error_message += f" Stderr: {stderr_output}"
            logger.error(error_message)
        else:
            logger.info(f"Opened file: {absolute_file_path}")

    except FileNotFoundError:
        # This typically means 'open', 'start', or 'xdg-open' command itself wasn't found
        logger.error(f"Error: Command for opening files ('open', 'start', or 'xdg-open') not found in PATH for system '{system}'.")
    except Exception as e:
        # Catch other potential exceptions
        logger.error(f"An unexpected error occurred while trying to run command to open file '{absolute_file_path}': {e}", exc_info=True)


def play_startup_sound():
    """Plays the startup sound relative to this script's location."""
    sound_filename = "alert.wav"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sound_file_path = os.path.join(script_dir, sound_filename)

    logger.info(f"Attempting to play startup sound from: {sound_file_path}")
    try:
        if not os.path.exists(sound_file_path):
            logger.error(f"Startup sound file not found at {sound_file_path}")
            return

        if platform.system() == "Darwin":  # macOS
            logger.info(f"Using 'afplay' on macOS for path: {sound_file_path}")
            result = subprocess.run(['afplay', sound_file_path], check=False, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("'afplay' completed successfully.")
            else:
                logger.error(f"'afplay' failed with code {result.returncode}. Error: {result.stderr}")
        else:  # Fallback for other systems (Windows, Linux)
            logger.info(f"Using 'playsound' for path: {sound_file_path}") # Log before call
            playsound(sound_file_path)
            logger.info(f"'playsound' call completed for: {sound_file_path}") # Log after call

        # logger.info("Startup sound played successfully.") # Removed as completion is logged above

    except Exception as e:
        # Catch potential errors
        logger.error(f"Failed to play startup sound '{sound_file_path}': {e}", exc_info=True)
