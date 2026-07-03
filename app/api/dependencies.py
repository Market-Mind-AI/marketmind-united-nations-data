from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.undata_service import UNDataService


def get_undata_service(session: Session = Depends(get_db)) -> Generator[UNDataService, None, None]:
    yield UNDataService(session)
