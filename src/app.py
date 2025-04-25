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
from . import jobs # Import the jobs module
import pytz # Add pytz import

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
                args=[form_url_to_schedule] # URLをリストとして渡す
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
                args=[excel_path_to_schedule] # パスをリストとして渡す
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
                 args=[]
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
    """指定されたスケジュールのジョブ（ファイルを開く、フォームを開く）を即時実行する"""
    db = SessionLocal()
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    db.close()

    if not schedule:
        logger.warning(f"Run now request for non-existent schedule ID: {schedule_id}")
        return jsonify({"error": f"Schedule with ID {schedule_id} not found"}), 404

    logger.info(f"Received run now request for schedule ID: {schedule_id} ('{schedule.description}')")
    success_excel = False
    success_form = False
    error_messages = []

    # Excelファイルを開く
    if schedule.excel_path:
        try:
            # jobs.py の関数を直接呼び出す
            # 注意: Excelパスが相対パスの場合、app.py実行時のカレントディレクトリからの相対パスになる
            # 絶対パスか、設定で基準パスを指定する方が安全
            base_path = os.getenv('EXCEL_BASE_PATH', '.') # .env などで基準パスを設定可能にする例
            full_excel_path = os.path.join(base_path, schedule.excel_path)
            logger.info(f"Attempting immediate open for Excel: {full_excel_path}")
            jobs.open_local_file(full_excel_path) # Use imported module
            success_excel = True
            logger.info(f"Successfully initiated immediate open for Excel: {full_excel_path}")
        except Exception as e:
            logger.error(f"Failed to immediately open Excel file for schedule {schedule_id}: {e}", exc_info=True)
            error_messages.append(f"Failed to open Excel: {e}")
    else:
        logger.info(f"No Excel path configured for immediate run of schedule {schedule_id}.")
        # Excelパスがないのはエラーではないので success_excel は True 扱いでも良いかも

    # Googleフォームを開く
    if schedule.google_form_url:
        try:
            logger.info(f"Attempting immediate open for Google Form: {schedule.google_form_url}")
            jobs.open_google_form(schedule.google_form_url) # Use imported module
            success_form = True
            logger.info(f"Successfully initiated immediate open for Google Form: {schedule.google_form_url}")
        except Exception as e:
            logger.error(f"Failed to immediately open Google Form for schedule {schedule_id}: {e}", exc_info=True)
            error_messages.append(f"Failed to open Google Form: {e}")
    else:
        logger.info(f"No Google Form URL configured for immediate run of schedule {schedule_id}.")
        # Google Form URLがないのはエラーではない

    if not error_messages:
        return jsonify({"status": "success", "message": f"Immediate report for schedule {schedule_id} initiated."}), 200
    else:
        # 何か一つでも失敗したらエラーレスポンス
        return jsonify({"status": "error", "message": "One or more actions failed.", "details": error_messages}), 500


# --- Main Execution --- 

if __name__ == '__main__':
    logger.info("Application starting...")
    # schedule_initial_jobs() # Temporarily disable initial job scheduling
    # logger.info("Scheduler started.") # Removed misplaced log
    logger.info("Starting Flask app...")
    # Run Flask app, disable reloader to prevent duplicate jobs in debug mode
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False) # Changed port to 5001
