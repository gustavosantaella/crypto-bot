from fastapi import APIRouter, HTTPException
from app.services.ai_service import AIService
from pydantic import BaseModel

router = APIRouter()

class AIRequest(BaseModel):
    symbol: str
    price: float
    rsi: float
    tp: float
    sl: float
    trade_type: str
    timeframe: str
    leverage: int
    atr_multiplier: float

@router.post("/analyze")
async def analyze_with_ai(request: AIRequest):
    """
    Consulta a DeepSeek para obtener un análisis probabilístico de la posición actual.
    """
    result = await AIService.analyze_market(request.dict())
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return result
