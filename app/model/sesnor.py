from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
from app.extension import db


class Sensor(db.Model):
    __tablename__ = "sensors"

    id = db.Column(db.Integer, primary_key=True)
    mac = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user_login = db.Column(db.String(60), db.ForeignKey("users.login"), nullable=False)
    user = relationship("User", back_populates="sensors")
    samples = relationship(
        "Sample", back_populates="sensor", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Sensor(mac='{self.mac}', name='{self.name}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "mac": self.mac,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "samples": [sample.to_dict() for sample in self.samples],
        }

    @classmethod
    def create_sensor(cls, mac, name, user_login):
        sensor = cls(mac=mac, name=name, user_login=user_login)
        db.session.add(sensor)
        db.session.commit()
        return sensor


class Sample(db.Model):
    __tablename__ = "samples"

    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey("sensors.id"), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    label = db.Column(db.String(255), nullable=False)
    watch_on_hand = db.Column(db.String(50), nullable=False)

    # Acceleration data - stored as PostgreSQL array [x, y, z]
    acceleration = db.Column(ARRAY(db.Float), nullable=False, default=[0.0, 0.0, 0.0])

    # Gyroscope data - stored as PostgreSQL array [x, y, z]
    gyroscope = db.Column(ARRAY(db.Float), nullable=False, default=[0.0, 0.0, 0.0])

    # Relationship to sensor
    sensor = relationship("Sensor", back_populates="samples")

    def __repr__(self):
        return f"<Sample(sensor_id={self.sensor_id}, timestamp='{self.timestamp}', label='{self.label}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "sensor_id": self.sensor_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "label": self.label,
            "watch_on_hand": self.watch_on_hand,
            "acceleration": self.acceleration or [0.0, 0.0, 0.0],
            "gyroscope": self.gyroscope or [0.0, 0.0, 0.0],
        }

    @classmethod
    def from_dict(
        cls, timestamp, label, watch_on_hand, acceleration, gyroscope, sensor_id
    ):
        """Create a Sample instance from dictionary data"""
        sample = cls(
            sensor_id=sensor_id,
            timestamp=timestamp,
            label=label,
            watch_on_hand=watch_on_hand,
            acceleration=acceleration,
            gyroscope=gyroscope,
        )

        return sample

    @classmethod
    def create_sample(
        cls, timestamp, label, watch_on_hand, acceleration, gyroscope, sensor_id
    ):
        sample = cls(
            sensor_id=sensor_id,
            timestamp=timestamp,
            label=label,
            watch_on_hand=watch_on_hand,
            acceleration=acceleration,
            gyroscope=gyroscope,
        )
        db.session.add(sample)
        db.session.commit()
        return sample
