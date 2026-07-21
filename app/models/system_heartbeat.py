from app.extensions import db


class SystemHeartbeat(db.Model):
    """
    Single-row table (id is always 1). Updated every ~30 seconds
    while the app is running (see app/heartbeat.py). Comparing
    last_seen at startup against "now" is how the app detects a real
    server outage and compensates active exam timers for it.
    """

    __tablename__ = "system_heartbeat"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    last_seen = db.Column(
        db.DateTime,
        nullable=False
    )