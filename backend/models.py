from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
import datetime
import database

class DeviceHealthRecord(database.Base):
    __tablename__ = "device_health"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    device_type = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    firmware = Column(String)
    health_data = Column(JSON)  # Store robust nested JSON
    issues = Column(JSON)       # Store list of strings

class TrafficMetricsRecord(database.Base):
    __tablename__ = "traffic_metrics"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    state_snapshot = Column(JSON)
    lane_metrics = Column(JSON)
    critical_events_this_minute = Column(JSON)
