from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.models.truck import Truck
from src.repositories.base import BaseRepository

class TruckRepository(BaseRepository[Truck]):
    """Repository handling Truck queries and database interactions."""

    def __init__(self, db: Session):
        super().__init__(Truck, db)

    def get_by_normalized_plate(self, normalized_plate: str) -> Optional[Truck]:
        return self.db.query(Truck).filter(Truck.normalized_plate == normalized_plate).first()

    def filter_trucks(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Truck], int]:
        query = self.db.query(Truck)
        if status:
            query = query.filter(Truck.status == status)
        if search:
            clean_search = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Truck.plate_number.ilike(clean_search),
                    Truck.normalized_plate.ilike(clean_search),
                    Truck.truck_type.ilike(clean_search)
                )
            )
        total = query.count()
        items = query.order_by(Truck.id.desc()).offset(skip).limit(limit).all()
        return items, total
