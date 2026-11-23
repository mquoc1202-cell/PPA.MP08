from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.models.driver import Driver
from src.repositories.base import BaseRepository

class DriverRepository(BaseRepository[Driver]):
    """Repository handling Driver data access and queries."""

    def __init__(self, db: Session):
        super().__init__(Driver, db)

    def get_by_code(self, driver_code: str) -> Optional[Driver]:
        return self.db.query(Driver).filter(Driver.driver_code == driver_code.strip().upper()).first()

    def filter_drivers(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Driver], int]:
        query = self.db.query(Driver)
        if status:
            query = query.filter(Driver.status == status)
        if search:
            clean_search = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Driver.driver_code.ilike(clean_search),
                    Driver.full_name.ilike(clean_search),
                    Driver.phone_number.ilike(clean_search)
                )
            )
        total = query.count()
        items = query.order_by(Driver.id.desc()).offset(skip).limit(limit).all()
        return items, total
