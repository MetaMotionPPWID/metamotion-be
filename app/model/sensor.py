from extension import db
from sqlalchemy import Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
import enum


class WatchHand(enum.Enum):
    LEFT = "left"
    RIGHT = "right"


class Sensor(db.Model):
    __tablename__ = "sensors"

    id = db.Column(db.Integer, primary_key=True)
    mac = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)

    # Relationships
    samples = relationship(
        "Sample", back_populates="sensor", cascade="all, delete-orphan"
    )
    username = db.Column(db.String, ForeignKey("users.login"), nullable=False)
    user = relationship("User", back_populates="sensors")

    @classmethod
    def create_sensor(cls, mac, name, username, samples=None):
        sensor = cls(mac=mac, name=name, username=username)
        db.session.add(sensor)
        db.session.flush()

        if samples:
            for sample_data in samples:
                Sample.create_sample(
                    sensor_id=sensor.id,
                    timestamp=datetime.fromisoformat(
                        sample_data["timestamp"].replace("Z", "+00:00")
                    ),
                    label=sample_data["label"],
                    watch_on_hand=WatchHand(sample_data["watch_on_hand"]),
                    acceleration=sample_data["acceleration"],
                    gyroscope=sample_data["gyroscope"],
                )

        db.session.commit()
        return sensor

    @classmethod
    def add_samples(cls, mac, samples):
        sensor = cls.get_sensor_by_mac(mac)
        for sample_data in samples:
            Sample.create_sample(
                sensor_id=sensor.id,
                timestamp=datetime.fromisoformat(
                    sample_data["timestamp"].replace("Z", "+00:00")
                ),
                label=sample_data["label"],
                watch_on_hand=WatchHand(sample_data["watch_on_hand"]),
                acceleration=sample_data["acceleration"],
                gyroscope=sample_data["gyroscope"],
            )
        return cls.get_sensor_by_mac(mac)

    @classmethod
    def get_user_sensors(cls, username):
        return cls.query.filter_by(username=username).all()

    @classmethod
    def get_sensor_by_mac(cls, mac):
        return cls.query.filter_by(mac=mac).first()

    def __repr__(self):
        return f"<Sensor(mac='{self.mac}', name='{self.name}')>"


class Sample(db.Model):
    __tablename__ = "samples"

    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, ForeignKey("sensors.id"), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    label = db.Column(db.String)
    watch_on_hand = db.Column(Enum(WatchHand), nullable=False)

    acceleration = db.Column(ARRAY(Float), nullable=False)
    gyroscope = db.Column(ARRAY(Float), nullable=False)

    # Relationship with sensor
    sensor = relationship("Sensor", back_populates="samples")

    @classmethod
    def create_sample(
        cls, sensor_id, timestamp, label, watch_on_hand, acceleration, gyroscope
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

    def __repr__(self):
        return f"<Sample(timestamp='{self.timestamp}', label='{self.label}')>"
