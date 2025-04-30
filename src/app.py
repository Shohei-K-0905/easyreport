import os
import sys
import logging
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

# ensure project root in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, jsonify, request, abort
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.base import JobLookupError
from sqlalchemy.orm import Session
from db import SessionLocal, engine, Base
from models import Schedule, ReportHistory
from .jobs import play_alert_sound, open_local_file, open_google_form
from config import settings
from . import jobs # Import the jobs module
import pytz # Add pytz import
import datetime # Ensure datetime is imported
# from flask_sse import sse # Import the sse blueprint
import json # Import json for SSE data

# --- Logging Setup (Revised) ---
# Configure root logger - good for general messages outside app context
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

# Get the root logger instance if needed elsewhere
root_logger = logging.getLogger()

# --- Database Setup ---
Base.metadata.create_all(bind=engine)

# --- App Configuration ---
# Get the base directory of the current file (src)
basedir = os.path.abspath(os.path.dirname(__file__))
# Define the absolute path to the templates directory (one level up)
template_dir = os.path.abspath(os.path.join(basedir, '..', 'templates'))
# Define the absolute path to the static directory (one level up)
static_dir = os.path.abspath(os.path.join(basedir, '..', 'static'))

# Initialize Flask app, specifying template and static folder locations
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# --- Configure Flask App Logging ---
# Ensure Flask logger uses the desired level and handlers
# Remove default Flask handler to avoid duplicate logs if basicConfig added one
# Note: In newer Flask versions, direct handler manipulation might differ slightly
from flask.logging import default_handler
app.logger.removeHandler(default_handler)

# Set Flask app logger level
app.logger.setLevel(logging.DEBUG)

# Add the handler configured by basicConfig (or configure a new one)
# Assuming basicConfig added a StreamHandler to the root logger
if root_logger.hasHandlers():
    for handler in root_logger.handlers:
        app.logger.addHandler(handler)
else:
    # Fallback if basicConfig didn't add a handler (e.g., running via flask run)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s'))
    app.logger.addHandler(stream_handler)

# Use app.logger for application-specific logs
logger = app.logger 

# --- Configure and Register SSE --- #
# If using Redis, configure the URL
# app.config["REDIS_URL"] = "redis://localhost" # Uncomment and adjust if you have Redis
# If not using Redis (using filesystem or in-memory, not recommended for production but ok for dev):
# app.config["SSE_STORAGE"] = "filesystem" # Or "memory" (less persistent)
# app.config["SSE_LISTENERS_PATH"] = "_sse_listeners" # Directory for filesystem storage

# Ensure the listener directory exists if using filesystem storage
# if app.config.get("SSE_STORAGE") == "filesystem":
#     listeners_path = os.path.join(app.root_path, '..', app.config["SSE_LISTENERS_PATH"])
#     os.makedirs(listeners_path, exist_ok=True)
#     logger.info(f"Ensured SSE listener directory exists: {listeners_path}")

# app.register_blueprint(sse, url_prefix='/stream') # Register the SSE blueprint

# --- APScheduler Setup ---
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
# Define the job store file path
jobstore_path = 'jobs.sqlite' # Assuming it's in the root directory relative to where app runs

# --- Ensure Clean Scheduler Start ---
# Delete the existing jobstore file before starting the scheduler
if os.path.exists(jobstore_path):
    try:
        os.remove(jobstore_path)
        logger.info(f"Removed existing jobstore file: {jobstore_path}")
    except OSError as e:
        logger.error(f"Error removing jobstore file {jobstore_path}: {e}")

# Timezoneを設定してSchedulerを初期化
scheduler = BackgroundScheduler(jobstores=jobstores, timezone=pytz.timezone('Asia/Tokyo'))

scheduler.start()
logger.info("Scheduler started.")

# --- Helper Functions for Job Management ---
def add_or_update_jobs_for_schedule(db_schedule: Schedule):
    """Adds or updates APScheduler jobs based on the Schedule object.

    Returns:
        bool: True if all operations were successful, False otherwise.
    """
    logger.info(f"Processing jobs for schedule {db_schedule.id} ('{db_schedule.description}')")
    # Use IntervalTrigger for interval-based scheduling
    if not db_schedule.interval_minutes or db_schedule.interval_minutes <= 0:
        logger.warning(f"Schedule {db_schedule.id} has invalid interval_minutes: {db_schedule.interval_minutes}. Skipping job scheduling.")
        # Decide if this case should be treated as success or failure for the caller
        # Let's assume it's a configuration issue, but not a scheduling *failure* per se.
        # If the schedule is active, perhaps it should be treated as failure?
        # For now, let's return True as the function itself didn't fail, but log a warning.
        return True

    trigger = IntervalTrigger(minutes=db_schedule.interval_minutes)
    # trigger_args is no longer needed

    # 各ジョブIDを定義
    form_job_id = f"schedule_{db_schedule.id}_google_form"
    excel_job_id = f"schedule_{db_schedule.id}_excel"
    sound_job_id = f"schedule_{db_schedule.id}_alert_sound"

    # Google Form URL と Excel Path を取得
    form_url_to_schedule = db_schedule.google_form_url
    excel_path_to_schedule = db_schedule.excel_path
    success = True # Track overall success

    # --- Google Form ジョブの処理 ---
    existing_form_job = scheduler.get_job(form_job_id)
    if db_schedule.is_active and form_url_to_schedule:
        logger.info(f"Scheduling/Updating Google Form job '{form_job_id}' for schedule {db_schedule.id} with URL: '{form_url_to_schedule}'")
        try:
            scheduler.add_job(
                jobs.open_google_form, # Use imported module
                trigger=trigger,
                id=form_job_id,
                name=f"Open Google Form for {db_schedule.description or db_schedule.id}",
                replace_existing=True,
                # Pass schedule_id FIRST, then the URL
                args=[db_schedule.id, form_url_to_schedule]
                # **trigger_args <- REMOVED
            )
            logger.info(f"Successfully scheduled/updated Google Form job '{form_job_id}'")
        except Exception as e:
            logger.error(f"Failed to schedule/update Google Form job '{form_job_id}': {e}", exc_info=True)
            success = False # Mark as failed
    elif existing_form_job:
        logger.info(f"Removing existing Google Form job '{form_job_id}' for schedule {db_schedule.id} (inactive or URL removed)")
        try:
            scheduler.remove_job(form_job_id)
            logger.info(f"Successfully removed Google Form job '{form_job_id}'")
        except JobLookupError:
            logger.warning(f"Tried to remove Google Form job '{form_job_id}', but it was not found.")
        except Exception as e:
            logger.error(f"Failed to remove Google Form job '{form_job_id}': {e}", exc_info=True)
            success = False # Mark as failed
    else:
         logger.info(f"No action needed for Google Form job '{form_job_id}' (schedule inactive or no URL, and no existing job).")

    # --- Excelファイルジョブの処理 ---
    existing_excel_job = scheduler.get_job(excel_job_id)
    if db_schedule.is_active and excel_path_to_schedule:
         logger.info(f"Scheduling/Updating Excel job '{excel_job_id}' for schedule {db_schedule.id} with path: '{excel_path_to_schedule}'")
         try:
             scheduler.add_job(
                jobs.open_local_file, # Use imported module
                trigger=trigger,
                id=excel_job_id,
                name=f"Open Excel for {db_schedule.description or db_schedule.id}",
                replace_existing=True,
                # Pass schedule_id FIRST, then the path
                args=[db_schedule.id, excel_path_to_schedule] 
                # **trigger_args <- REMOVED
             )
             logger.info(f"Successfully scheduled/updated Excel job '{excel_job_id}'")
         except Exception as e:
            logger.error(f"Failed to schedule/update Excel job '{excel_job_id}': {e}", exc_info=True)
            success = False # Mark as failed
    elif existing_excel_job:
         logger.info(f"Removing existing Excel job '{excel_job_id}' for schedule {db_schedule.id} (inactive or path removed)")
         try:
             scheduler.remove_job(excel_job_id)
             logger.info(f"Successfully removed Excel job '{excel_job_id}'")
         except JobLookupError:
             logger.warning(f"Tried to remove Excel job '{excel_job_id}', but it was not found.")
         except Exception as e:
             logger.error(f"Failed to remove Excel job '{excel_job_id}': {e}", exc_info=True)
             success = False # Mark as failed
    else:
         logger.info(f"No action needed for Excel job '{excel_job_id}' (schedule inactive or no path, and no existing job).")

    # --- アラート音ジョブの処理 ---
    existing_sound_job = scheduler.get_job(sound_job_id)
    if db_schedule.is_active:
         logger.info(f"Scheduling/Updating Alert Sound job '{sound_job_id}' for schedule {db_schedule.id}")
         try:
             scheduler.add_job(
                 jobs.play_alert_sound, # Use imported module
                 trigger=trigger,
                 id=sound_job_id,
                 name=f"Alert Sound for {db_schedule.description or db_schedule.id}",
                 replace_existing=True,
                 args=[db_schedule.id] # Pass the schedule ID
                 # **trigger_args <- REMOVED
             )
             logger.info(f"Successfully scheduled/updated Alert Sound job '{sound_job_id}'")
         except Exception as e:
            logger.error(f"Failed to schedule/update Alert Sound job '{sound_job_id}': {e}", exc_info=True)
            success = False # Mark as failed
    elif existing_sound_job:
         logger.info(f"Removing existing Alert Sound job '{sound_job_id}' for schedule {db_schedule.id} (inactive)")
         try:
             scheduler.remove_job(sound_job_id)
             logger.info(f"Successfully removed Alert Sound job '{sound_job_id}'")
         except JobLookupError:
             logger.warning(f"Tried to remove Alert Sound job '{sound_job_id}', but it was not found.")
         except Exception as e:
             logger.error(f"Failed to remove Alert Sound job '{sound_job_id}': {e}", exc_info=True)
             success = False # Mark as failed
    else:
        logger.info(f"No action needed for Alert Sound job '{sound_job_id}' (schedule inactive and no existing job).")

    return success # Return the overall success status

def remove_jobs_for_schedule(schedule_id: int):
    """Removes APScheduler jobs associated with a schedule ID."""
    form_job_id = f"schedule_{schedule_id}_google_form"
    excel_job_id = f"schedule_{schedule_id}_excel"
    sound_job_id = f"schedule_{schedule_id}_alert_sound"
    try:
        scheduler.remove_job(form_job_id)
        logger.info(f"Removed Google Form job {form_job_id}")
    except JobLookupError:
        pass
    except Exception as e:
        logger.error(f"Error removing Google Form job {form_job_id}: {e}")

    try:
        scheduler.remove_job(excel_job_id)
        logger.info(f"Removed Excel job {excel_job_id}")
    except JobLookupError:
        pass
    except Exception as e:
        logger.error(f"Error removing Excel job {excel_job_id}: {e}")

    try:
        scheduler.remove_job(sound_job_id)
        logger.info(f"Removed Alert Sound job {sound_job_id}")
    except JobLookupError:
        pass
    except Exception as e:
        logger.error(f"Error removing Alert Sound job {sound_job_id}: {e}")


# --- Initial Job Scheduling (on startup) ---
def schedule_initial_jobs():
    """Loads active schedules from DB and schedules them using IntervalTrigger."""
    logger.info("Scheduling initial jobs from database...")
    db = SessionLocal()
    schedules_added = 0
    schedules_failed = 0
    try:
        # Load active schedules that have a positive interval_minutes value
        active_schedules = db.query(Schedule).filter(Schedule.is_active == True, Schedule.interval_minutes > 0).all()
        logger.info(f"Found {len(active_schedules)} active schedules with intervals in the database for initial scheduling.")
        for db_schedule in active_schedules:
             if add_or_update_jobs_for_schedule(db_schedule):
                 schedules_added += 1
             else:
                 # Error already logged in add_or_update_jobs_for_schedule
                 schedules_failed += 1
    except Exception as e:
        logger.error(f"Error during initial job scheduling: {e}", exc_info=True)
        schedules_failed = -1 # Indicate overall failure
    finally:
        db.close()
        logger.info(f"Initial job scheduling complete. Success: {schedules_added}, Failed: {schedules_failed if schedules_failed >= 0 else 'N/A (Error)'}")


# --- Internal API Endpoints (Not for direct user access) ---
@app.route('/internal/notify_alert/<int:schedule_id>', methods=['POST'])
def notify_alert_triggered(schedule_id):
    """Internal endpoint called by jobs.py when an alert sound plays.
       Publishes an SSE event to notify the frontend.
    """
    logger.info(f"Received internal notification: Alert triggered for schedule_id {schedule_id}")
    # Publish an event named 'alert_triggered' with the schedule_id
    # sse.publish({"schedule_id": schedule_id}, type='alert_triggered')
    # logger.info(f"Published SSE event 'alert_triggered' for schedule_id {schedule_id}")
    logger.warning(f"SSE functionality is temporarily disabled. Skipping SSE publish for schedule {schedule_id}.")
    return jsonify({"status": "success", "message": "SSE disabled"}), 200

@app.route('/internal/mark_report_action_completed/<int:schedule_id>', methods=['POST'])
def internal_mark_completed(schedule_id):
    """Internal endpoint called by scheduled jobs after actions complete."""
    logger.info(f"Internal request received to mark report action completed for schedule_id: {schedule_id}")
    # Call the existing function, but handle its boolean return value
    success = mark_report_completed(schedule_id) 
    if success:
        logger.info(f"Internal mark completed successful for schedule_id: {schedule_id}")
        return jsonify({"status": "success"}), 200
    else:
        logger.error(f"Internal mark completed failed for schedule_id: {schedule_id}")
        # Return 500 to indicate failure to the calling job
        return jsonify({"status": "error", "message": "Failed to mark completion internally"}), 500

# --- Flask Routes --- 

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/history')
def history_page():
    return render_template('history.html')

@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    """Returns a list of all schedules."""
    db = SessionLocal()
    try:
        schedules = db.query(Schedule).order_by(Schedule.id).all()
        return jsonify([
            {
                'id': s.id,
                'description': s.description,
                'interval_minutes': s.interval_minutes,
                'is_active': s.is_active,
                'next_run_time': scheduler.get_job(f"schedule_{s.id}_alert_sound").next_run_time.isoformat() if s.is_active and scheduler.get_job(f"schedule_{s.id}_alert_sound") else None,
                'last_run_time': s.last_run_time.isoformat() if s.last_run_time else None,
                'excel_path': s.excel_path,
                'google_form_url': s.google_form_url
            }
            for s in schedules
        ])
    except Exception as e:
        logger.error(f"Error fetching schedules: {e}")
        return jsonify({"error": "Failed to fetch schedules"}), 500
    finally:
        db.close()

def schedule_to_dict(schedule):
    return {
        "id": schedule.id,
        "description": schedule.description,
        "interval_minutes": schedule.interval_minutes,
        "is_active": schedule.is_active,
        "excel_path": schedule.excel_path,
        "google_form_url": schedule.google_form_url
    }

@app.route('/api/schedules', methods=['POST'])
def add_schedule():
    data = request.get_json()
    description = data.get('description')
    interval_minutes = data.get('interval_minutes', 0)
    excel_path = data.get('excel_path')
    google_form_url = data.get('google_form_url') # Get Google Form URL
    is_active = data.get('is_active', True)

    if not description:
        abort(400, description="Missing description")

    # Validate interval
    if not isinstance(interval_minutes, int) or interval_minutes <= 0:
        abort(400, description="Invalid interval_minutes, must be a positive integer.")

    db = SessionLocal()
    new_schedule_id = None # To store the ID even if commit fails later
    try:
        new_schedule = Schedule(
            description=description,
            interval_minutes=interval_minutes,
            excel_path=excel_path,
            google_form_url=google_form_url, # Save Google Form URL
            is_active=is_active
        )
        db.add(new_schedule)
        db.flush()  # Assign an ID by flushing the session
        new_schedule_id = new_schedule.id # Get the ID before potential rollback

        # Schedule the job using the interval
        if is_active:
            if not add_or_update_jobs_for_schedule(new_schedule):
                # If job scheduling fails, the transaction will be rolled back.
                raise Exception(f"Failed to schedule jobs for new schedule {new_schedule_id}")
            else:
                logger.info(f"Jobs scheduled successfully for new schedule {new_schedule_id}")
        else:
             logger.info(f"New schedule {new_schedule_id} created but is inactive. No jobs scheduled.")

        # If everything succeeded, commit the transaction
        db.commit()
        db.refresh(new_schedule) # Refresh to get the final state after commit

        logger.info(f"Successfully added and committed schedule {new_schedule_id}")
        return jsonify(schedule_to_dict(new_schedule)), 201 # Use helper function

    except Exception as e:
        db.rollback() # Rollback any changes if error occurred during add, flush, or job scheduling
        logger.error(f"Error adding schedule or scheduling jobs for potential schedule {new_schedule_id if new_schedule_id else '(unknown ID)'}: {e}", exc_info=True)
        error_message = f"Failed to schedule jobs for the new schedule (ID: {new_schedule_id})." if new_schedule_id else "Failed to add schedule to database."
        # Consider returning 500 if it was a server-side issue during job scheduling
        # or 400 if it might be related to bad input data (though validation should catch that)
        status_code = 500
        return jsonify({"error": error_message, "details": str(e)}), status_code
    finally:
        db.close()

@app.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    data = request.get_json()
    db = SessionLocal()
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        db.close()
        return jsonify({"error": "Schedule not found"}), 404

    # 更新可能なフィールドをループで処理
    allowed_updates = ['description', 'interval_minutes', 'excel_path', 'google_form_url', 'is_active']
    update_occurred = False
    for key in allowed_updates:
        if key in data:
            # interval_minutes は整数に変換、ただし None は許可
            if key == 'interval_minutes':
                value = data[key]
                if value is not None and value != '':
                     try:
                         setattr(schedule, key, int(value))
                         update_occurred = True
                     except (ValueError, TypeError):
                         db.rollback()
                         db.close()
                         return jsonify({"error": f"Invalid value for {key}: must be an integer"}), 400
                elif getattr(schedule, key) is not None: # 既存がNoneでない場合のみ更新
                     setattr(schedule, key, None)
                     update_occurred = True
            # is_active はブール値に変換
            elif key == 'is_active':
                value = data[key]
                if isinstance(value, bool):
                    if getattr(schedule, key) != value:
                        setattr(schedule, key, value)
                        update_occurred = True
                else: # 文字列 'true'/'false' などは考慮しない場合はエラー
                    db.rollback()
                    db.close()
                    return jsonify({"error": f"Invalid value for {key}: must be true or false"}), 400
            # その他のフィールド
            elif getattr(schedule, key) != data[key]:
                setattr(schedule, key, data[key])
                update_occurred = True

    if update_occurred:
        try:
            db.commit()
            logger.info(f"Schedule {schedule_id} updated successfully.")
            # スケジュールが更新されたので、関連するジョブも更新/削除
            add_or_update_jobs_for_schedule(schedule)
            db.refresh(schedule) # 更新後の情報を反映
        except Exception as e:
            db.rollback()
            logger.error(f"Error committing schedule update for ID {schedule_id}: {e}", exc_info=True)
            return jsonify({"error": "Database error during update."}), 500
        finally:
            db.close()
    else:
        logger.info(f"No changes detected for schedule {schedule_id}. Update skipped.")
        db.close()

    # 更新後のスケジュール情報を返す (更新がなくても現在の情報を返す)
    schedule_dict = {c.name: getattr(schedule, c.name) for c in schedule.__table__.columns}
    return jsonify(schedule_dict)

@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Deletes a schedule."""
    db = SessionLocal()
    try:
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            abort(404, description="Schedule not found")

        remove_jobs_for_schedule(schedule_id)

        db.delete(schedule)
        db.commit()
        logger.info(f"Deleted schedule ID: {schedule_id}")
        return jsonify({'message': 'Schedule deleted successfully'}), 200

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting schedule {schedule_id}: {e}")
        return jsonify({"error": "Failed to delete schedule"}), 500
    finally:
        db.close()

@app.route('/api/schedules/<int:schedule_id>/run_now', methods=['POST'])
def run_schedule_now(schedule_id):
    logger.info(f"===>>> run_schedule_now function entered for schedule_id: {schedule_id} <<<===")
    logger.info(f"Received request to run schedule {schedule_id} immediately.")
    session = SessionLocal()
    schedule = session.query(Schedule).filter(Schedule.id == schedule_id).first()
    session.close() # Close session after fetching schedule

    if not schedule:
        logger.warning(f"Immediate run failed: Schedule ID {schedule_id} not found.")
        return jsonify({"status": "error", "message": "Schedule not found"}), 404

    if not schedule.is_active:
        logger.warning(f"Attempted to run inactive schedule {schedule_id} immediately.")
        return jsonify({"status": "error", "message": "Schedule is inactive"}), 400

    logger.info(f"Executing actions immediately for schedule {schedule_id}")
    actions_executed = False

    # --- Execute Actions --- 
    try:
        # 1. Open Excel File (if path exists)
        if schedule.excel_path: 
            logger.info(f"Running open_local_file job immediately for schedule {schedule_id}")
            jobs.open_local_file(schedule_id, schedule.excel_path)
            actions_executed = True

        # 2. Open Google Form (if URL exists)
        if schedule.google_form_url:
            logger.info(f"Running open_google_form job immediately for schedule {schedule_id}")
            jobs.open_google_form(schedule_id, schedule.google_form_url)
            actions_executed = True

        # --- Mark completion if actions were attempted and successful --- 
        if actions_executed:
            logger.info(f"Immediate run actions completed for schedule {schedule_id}. Attempting to mark history.")
            # Call mark_report_completed internally (does not use request context)
            mark_success = mark_report_completed(schedule_id)
            if not mark_success:
                 logger.error(f"Failed to mark history for immediate run of schedule {schedule_id} even though actions succeeded.")
                 # Decide if this should be a 500 error or just a warning
                 return jsonify({"status": "error", "message": "Failed to record completion in history."}), 500
    except Exception as e:
        logger.error(f"Error executing immediate run for schedule {schedule_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error executing immediate run"}), 500

    return jsonify({"status": "success", "message": f"Immediate report for schedule {schedule_id} initiated and completed."}), 200

@app.route('/api/report_history')
def get_report_history():
    session = SessionLocal()
    logger.info("Attempting to fetch report history...")
    try:
        history_records = (
            session.query(
                ReportHistory.id,
                ReportHistory.schedule_id,
                ReportHistory.completed_at,
                Schedule.description.label('schedule_description')
            )
            .join(Schedule, ReportHistory.schedule_id == Schedule.id)
            .order_by(ReportHistory.completed_at.desc())
            .all()
        )
        logger.info(f"Successfully fetched {len(history_records)} records from database.")

        history_list = []
        logger.info("Attempting to serialize history records loop...")
        for record in history_records:
            try:
                logger.debug(f"Processing record: id={record.id}, schedule_id={record.schedule_id}, completed_at={record.completed_at}, description={record.schedule_description}") 
                completed_at_iso = record.completed_at.isoformat() + 'Z' if record.completed_at else None
                history_list.append({
                    'id': record.id,
                    'schedule_id': record.schedule_id,
                    'completed_at': completed_at_iso,
                    'schedule_description': record.schedule_description
                })
                logger.debug(f"Successfully processed record id={record.id}")
            except Exception as loop_e:
                logger.error(f"Error processing record id={record.id}: {loop_e}", exc_info=True)
                raise # Re-raise the exception to trigger the outer except block
        
        logger.info("Successfully serialized all history records.")
        return jsonify(history_list)
    except Exception as e:
        logger.error(f"Error fetching report history (outer try): {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch report history"}), 500
    finally:
        logger.info("Closing session for report history fetch.")
        session.close()

@app.route('/api/schedules/<int:schedule_id>/mark_completed', methods=['POST'])
def mark_report_completed(schedule_id):
    logger.info(f"Attempting to mark report completed for schedule_id: {schedule_id}") # Log entry
    db = SessionLocal()
    try:
        # Check if the schedule actually exists
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            logger.warning(f"Mark completion failed: Schedule ID {schedule_id} not found.")
            # Avoid abort(404) if called internally, maybe return False or raise specific exception?
            # For now, just log and return error response if called via API
            if request: # Check if called via HTTP request
                 abort(404, description="Schedule not found")
            else:
                return False # Indicate failure if called internally

        logger.debug(f"Found schedule: {schedule.description}. Creating history entry.")
        new_history = ReportHistory(schedule_id=schedule_id)
        db.add(new_history)
        db.commit()
        logger.info(f"Successfully marked report completed and committed for schedule_id: {schedule_id}")
        # If called via API, return success
        if request:
            return jsonify({"status": "success", "message": f"Report for schedule {schedule_id} marked as completed."}), 200
        else:
             return True # Indicate success if called internally
    except Exception as e:
        logger.error(f"Error marking report completed for schedule_id {schedule_id}: {e}", exc_info=True)
        db.rollback() # Rollback on error
        # If called via API, return error
        if request:
             abort(500, description="Failed to mark report as completed")
        else:
            return False # Indicate failure if called internally
    finally:
        logger.debug(f"Closing session after attempting to mark completion for schedule_id: {schedule_id}")
        db.close()

# --- Main Execution (Only used if running the script directly with 'python src/app.py') ---
if __name__ == '__main__':
    # This block is typically NOT executed when using 'flask run'
    logger.info(f"Starting Flask app directly via __main__ on port {settings.PORT}...")
    # The following lines are removed as flask run handles this.
    # logger.info("Attempting to call jobs.play_startup_sound()...") # Log before call attempt
    # try:
    #     jobs.play_startup_sound()
    #     logger.info("Call to jobs.play_startup_sound() completed (within try block).") # Log after successful call
    # except Exception as e:
    #     logger.error(f"Error occurred *during* the call to jobs.play_startup_sound(): {e}", exc_info=True)

    # Flask アプリケーションを実行
    # host='0.0.0.0' は全てのネットワークインターフェースで待ち受ける
    # debug=True にすると、コード変更時に自動リロードされ、デバッグ情報が表示される
    # use_reloader=False は、APSchedulerとの二重起動を防ぐために重要
    app.run(host='127.0.0.1', port=settings.PORT, debug=False, use_reloader=False) # Set debug=False typically for direct run
    logger.info("Flask app started directly via __main__.")
