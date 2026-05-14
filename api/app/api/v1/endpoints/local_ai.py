from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.local_ai_service import LocalAIService

router = APIRouter()

@router.get("/predict")
def get_local_prediction(look_ahead: int = 5, k: int = 5, db: Session = Depends(get_db)):
    """
    Entrena un modelo KNN con la mitad de los datos de price_logs
    y predice con la otra mitad.
    """
    result = LocalAIService.train_and_predict(db, look_ahead=look_ahead, k_neighbors=k)
    return result