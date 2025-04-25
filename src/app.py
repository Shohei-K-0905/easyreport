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
from models import Schedule
from src.jobs import play_alert_sound, open_local_file, open_google_form
from config import settings

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

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

# --- APScheduler Setup ---
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
scheduler = BackgroundScheduler(jobstores=jobstores)

# --- Helper Functions for Job Management ---
def add_or_update_jobs_for_schedule(db_schedule: Schedule):
    """Adds or updates APScheduler jobs based on the Schedule object."""
    job_id_alert = f'alert_{db_schedule.id}'
    job_id_form = f'form_{db_schedule.id}'
    job_id_file = f'{db_schedule.id}_open_file'
    job_name_alert = f'Alert Sound for {db_schedule.description}'
    job_name_form = f'Open Google Form for {db_schedule.description}'
    job_name_file = f'Open file for Schedule {db_schedule.id}'

    # Remove existing jobs first to ensure clean state
    if scheduler.get_job(job_id_alert):
        scheduler.remove_job(job_id_alert)
        logger.info(f"Removed existing alert job {job_id_alert}")
    if scheduler.get_job(job_id_form):
        scheduler.remove_job(job_id_form)
        logger.info(f"Removed existing form job {job_id_form}")
    if scheduler.get_job(job_id_file):
        scheduler.remove_job(job_id_file)
        logger.info(f"Removed existing file open job {job_id_file}")

    # Add jobs only if the schedule is active and has a positive interval
    if db_schedule.is_active and db_schedule.interval_minutes > 0:
        trigger = IntervalTrigger(minutes=db_schedule.interval_minutes)
        
        # Schedule alert sound job
        scheduler.add_job(
            play_alert_sound,
            trigger=trigger,
            id=job_id_alert,
            name=job_name_alert,
            replace_existing=True # Should be redundant due to removal above, but safe
        )
        logger.info(f"Scheduled alert sound job '{job_id_alert}' for schedule {db_schedule.id} with interval: {db_schedule.interval_minutes} minutes")

        # Schedule Google Form opening job only if URL is provided
        if db_schedule.google_form_url:
            form_url_to_schedule = db_schedule.google_form_url
            logger.info(f"Attempting to schedule open_google_form job '{job_id_form}' with URL: '{form_url_to_schedule}'")
            scheduler.add_job(
                'src.jobs:open_google_form',
                trigger=trigger,
                id=job_id_form,
                name=job_name_form,
                replace_existing=True,
                args=(form_url_to_schedule,), # <--- 変更点: カンマを追加してタプルにする
            )
            logger.info(f"Scheduled open form job '{job_id_form}' for schedule {db_schedule.id} with interval: {db_schedule.interval_minutes} minutes")
        else:
             logger.info(f"No Google Form URL provided for schedule {db_schedule.id}, skipping form job.")

        # Schedule local file opening job only if excel_path is provided
        if db_schedule.excel_path:
            scheduler.add_job(
                open_local_file,
                trigger=trigger,
                args=[db_schedule.excel_path],
                id=job_id_file,
                name=job_name_file,
                replace_existing=True,
            )
            logger.info(f"Scheduled file open job {job_id_file} for schedule {db_schedule.id} with interval {db_schedule.interval_minutes} minutes.")
        else:
            # If excel_path was removed, remove the corresponding job if it exists
            if scheduler.get_job(job_id_file):
                scheduler.remove_job(job_id_file)
                logger.info(f"Removed file open job {job_id_file} as path is now empty.")

    return True # Indicate success


def remove_jobs_for_schedule(schedule_id: int):
    """Removes APScheduler jobs associated with a schedule ID."""
    job_id_alert = f'alert_{schedule_id}'
    job_id_form = f'form_{schedule_id}'
    job_id_file = f'{schedule_id}_open_file'
    try:
        scheduler.remove_job(job_id_alert)
        logger.info(f"Removed alert job {job_id_alert}")
    except JobLookupError:
        pass
    except Exception as e:
        logger.error(f"Error removing alert job {job_id_alert}: {e}")

    try:
        scheduler.remove_job(job_id_form)
        logger.info(f"Removed form job {job_id_form}")
    except JobLookupError:
        pass
    except Exception as e:
        logger.error(f"Error removing form job {job_id_form}: {e}")

    try:
        scheduler.remove_job(job_id_file)
        logger.info(f"Removed file open job {job_id_file}")
    except JobLookupError:
        pass
    except Exception as e:
        logger.error(f"Error removing file open job {job_id_file}: {e}")


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


# --- Flask Routes --- 

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

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
                'next_run_time': scheduler.get_job(f'alert_{s.id}').next_run_time.isoformat() if s.is_active and scheduler.get_job(f'alert_{s.id}') else None,
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
    try:
        new_schedule = Schedule(
            description=description, 
            interval_minutes=interval_minutes,
            excel_path=excel_path,
            google_form_url=google_form_url, # Save Google Form URL
            is_active=is_active
        )
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)

        # Schedule the job using the interval
        if not add_or_update_jobs_for_schedule(new_schedule):
            # Handle scheduling failure (e.g., rollback DB or mark as inactive)
            db.rollback()
            logger.error(f"Failed to schedule jobs for new schedule {new_schedule.id}, rolling back DB add.")
            abort(500, "Failed to schedule jobs for the new schedule.")

        logger.info(f"Added new schedule: {new_schedule}")
        return jsonify({
            "id": new_schedule.id,
            "description": new_schedule.description,
            "interval_minutes": new_schedule.interval_minutes,
            "is_active": new_schedule.is_active,
            "excel_path": new_schedule.excel_path,
            "google_form_url": new_schedule.google_form_url
        }), 201
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding schedule: {e}")
        return jsonify({"error": "Failed to add schedule to database"}), 500
    finally:
        db.close()

@app.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        return jsonify({"error": "Schedule not found"}), 404

    data = request.get_json()
    db_schedule.description = data.get('description', db_schedule.description)
    db_schedule.interval_minutes = data.get('interval_minutes', db_schedule.interval_minutes)
    db_schedule.excel_path = data.get('excel_path', db_schedule.excel_path) # Allow clearing the path
    db_schedule.google_form_url = data.get('google_form_url', db_schedule.google_form_url) # Get and update Google Form URL
    db_schedule.is_active = data.get('is_active', db_schedule.is_active)

    try:
        db.commit()
        # Recalculate or update job if interval or active status changes
        needs_job_update = False
        if 'interval_minutes' in data or 'is_active' in data or 'excel_path' in data or 'google_form_url' in data:
            needs_job_update = True

        # If schedule is being deactivated, remove jobs
        if db_schedule.is_active is False:
            remove_jobs_for_schedule(schedule_id)

        if needs_job_update:
            # Remove existing jobs first if they exist
            remove_jobs_for_schedule(schedule_id)

            # Add or update jobs based on the new state (active or inactive)
            # Only schedule if active and interval is valid
            if db_schedule.is_active and db_schedule.interval_minutes and db_schedule.interval_minutes > 0:
                if not add_or_update_jobs_for_schedule(db_schedule):
                    # If scheduling fails after update, rollback or handle error
                    db.rollback()
                    logger.error(f"Failed to reschedule jobs for schedule {schedule_id} after update, rolling back.")
                    abort(500, "Failed to reschedule jobs after update.")
            else:
                logger.info(f"Jobs for schedule {schedule_id} remain removed (inactive or invalid interval). Active: {db_schedule.is_active}, Interval: {db_schedule.interval_minutes}")

        logger.info(f"Updated schedule {schedule_id}: Active={db_schedule.is_active}, Interval={db_schedule.interval_minutes}")
        return jsonify({
            "id": db_schedule.id,
            "description": db_schedule.description,
            "interval_minutes": db_schedule.interval_minutes,
            "is_active": db_schedule.is_active,
            "excel_path": db_schedule.excel_path,
            "google_form_url": db_schedule.google_form_url
        })
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating schedule {schedule_id}: {e}")
        return jsonify({"error": "Failed to update schedule"}), 500
    finally:
        db.close()

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


# --- Main Execution --- 

if __name__ == '__main__':
    logger.info("Application starting...")
    schedule_initial_jobs()
    scheduler.start()
    logger.info("Scheduler started.")
    logger.info("Starting Flask app...")
    # Run Flask app, disable reloader to prevent duplicate jobs in debug mode
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False) # use_reloader=False を追加
