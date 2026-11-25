import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from src.core.database import Base


class TripStatus(str, enum.Enum):
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Trip(Base):
    """
    SQLAlchemy Model for Trip (Chuyến Hàng).
    Canonical constraints cited from data-model.md:
    - Trip.reference_code: VARCHAR(50), NOT NULL, UNIQUE, INDEX
    - Trip.cargo_weight_kg: INTEGER, NOT NULL, CHECK (cargo_weight_kg > 0)
    - Trip.status: VARCHAR(20), NOT NULL, DEFAULT 'UNASSIGNED', CHECK status IN ('UNASSIGNED', 'ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED', 'CANCELLED')
    - Trip.assigned_truck_id: INTEGER, NULL, FOREIGN KEY (trucks.id)
    - Trip.assigned_driver_id: INTEGER, NULL, FOREIGN KEY (drivers.id)
    """
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint(
            "status IN ('UNASSIGNED', 'ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED', 'CANCELLED')",
            name="ck_trip_status_valid"
        ),
        CheckConstraint("cargo_weight_kg > 0", name="ck_trip_cargo_weight_positive"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reference_code = Column(String(50), nullable=False, unique=True, index=True)
    sender_name = Column(String(100), nullable=False)
    sender_phone = Column(String(20), nullable=False)
    pickup_address = Column(String(255), nullable=False)
    delivery_address = Column(String(255), nullable=False)
    cargo_weight_kg = Column(Integer, nullable=False)
    cargo_type = Column(String(100), nullable=False)
    estimated_start_time = Column(DateTime, nullable=True)
    estimated_end_time = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default=TripStatus.UNASSIGNED.value)
    assigned_truck_id = Column(Integer, ForeignKey("trucks.id"), nullable=True)
    assigned_driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    actual_cargo_weight_kg = Column(Integer, nullable=True)
    handover_person = Column(String(100), nullable=True)
    cargo_condition = Column(String(255), nullable=True)
    discrepancy_notes = Column(String(500), nullable=True)
    actual_pickup_time = Column(DateTime, nullable=True)
    actual_depart_time = Column(DateTime, nullable=True)
    pickup_recorded_at = Column(DateTime, nullable=True)
    depart_recorded_at = Column(DateTime, nullable=True)
    actual_delivery_time = Column(DateTime, nullable=True)
    actual_completed_time = Column(DateTime, nullable=True)
    recipient_name = Column(String(100), nullable=True)
    delivery_notes = Column(String(500), nullable=True)
    delivery_recorded_at = Column(DateTime, nullable=True)
    completed_recorded_at = Column(DateTime, nullable=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    truck = relationship("Truck", foreign_keys=[assigned_truck_id])
    driver = relationship("Driver", foreign_keys=[assigned_driver_id])
    events = relationship("TripEvent", back_populates="trip", cascade="all, delete-orphan", order_by="TripEvent.actual_time.asc()")
    evidence = relationship("TripEvidence", back_populates="trip", cascade="all, delete-orphan", order_by="TripEvidence.created_at.asc()")
    issues = relationship("TripIssue", back_populates="trip", cascade="all, delete-orphan", order_by="TripIssue.created_at.desc()")

    @property
    def is_delayed(self) -> bool:
        """Kiểm tra chuyến hàng có bị quá hạn cam kết vận hành hay không."""
        if self.status in [TripStatus.DELIVERED.value, TripStatus.COMPLETED.value, TripStatus.CANCELLED.value]:
            return False
        if not self.estimated_end_time:
            return False
        return datetime.now() > self.estimated_end_time

    @property
    def has_open_issues(self) -> bool:
        """Kiểm tra chuyến hàng có sự cố nào đang ở trạng thái OPEN hay không."""
        if not self.issues:
            return False
        return any(getattr(issue, "status", None) == "OPEN" for issue in self.issues)
