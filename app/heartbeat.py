import threading
import time as time_module
from datetime import datetime, timedelta

from app.extensions import db
from app.models.system_heartbeat import SystemHeartbeat
from app.models.exam_progress import ExamProgress
from app.logger import app_logger


# Gaps shorter than this are treated as a normal restart (the process
# reloading takes a few seconds) rather than a real outage worth
# compensating for. Raise this if your normal restarts routinely take
# longer than 30 seconds and you're seeing false compensation.
DOWNTIME_THRESHOLD_SECONDS = 30

# How often the background thread refreshes last_seen while the app
# is running. This is also roughly the smallest outage the app can
# reliably detect -- a shorter gap than this may not register.
HEARTBEAT_INTERVAL_SECONDS = 30


def apply_downtime_compensation():
    """
    Runs once at startup, before the app starts serving requests.

    Compares "the last time this app was confirmed running" against
    "now." If the gap is large enough to be a genuine server outage
    (not just the normal few seconds a restart takes), every
    currently in-progress exam has its end_time pushed back by that
    same amount -- so a student mid-exam doesn't lose time to
    something that was entirely the server's fault, not theirs.

    Deliberately does NOT compensate for an individual student's own
    disconnect while the server stayed up and running for everyone
    else -- that's a different situation, and pausing a student's own
    timer just because THEIR connection dropped would be trivially
    exploitable (close the tab any time you want extra time). This
    only fires for a genuine server-wide outage, which by definition
    isn't something any single student can trigger.
    """

    heartbeat = SystemHeartbeat.query.get(1)

    now = datetime.now()

    if heartbeat is None:

        # First time this app has ever started with heartbeat
        # tracking in place -- nothing to compare against yet.
        db.session.add(
            SystemHeartbeat(id=1, last_seen=now)
        )

        db.session.commit()

        return

    downtime_seconds = (now - heartbeat.last_seen).total_seconds()

    if downtime_seconds > DOWNTIME_THRESHOLD_SECONDS:

        active_progress = ExamProgress.query.all()

        for progress in active_progress:

            progress.end_time = progress.end_time + timedelta(
                seconds=downtime_seconds
            )

        app_logger.warning(
            f"SERVER DOWNTIME DETECTED | "
            f"Duration={int(downtime_seconds)}s | "
            f"Extended {len(active_progress)} active exam(s) by "
            f"that amount so nobody loses exam time to the outage."
        )

    heartbeat.last_seen = now

    db.session.commit()


def start_heartbeat_thread(app):
    """
    Keeps SystemHeartbeat.last_seen fresh roughly every 30 seconds for
    as long as this process is alive. This is what makes the NEXT
    startup's downtime calculation possible -- without a continuously
    updated "last known alive" timestamp, there'd be nothing to
    measure the gap against.

    Runs as a daemon thread so it never blocks the app from shutting
    down cleanly.
    """

    def heartbeat_loop():

        with app.app_context():

            while True:

                try:

                    heartbeat = SystemHeartbeat.query.get(1)

                    if heartbeat:

                        heartbeat.last_seen = datetime.now()
                        db.session.commit()

                except Exception:

                    db.session.rollback()

                time_module.sleep(HEARTBEAT_INTERVAL_SECONDS)

    thread = threading.Thread(
        target=heartbeat_loop,
        daemon=True,
    )

    thread.start()