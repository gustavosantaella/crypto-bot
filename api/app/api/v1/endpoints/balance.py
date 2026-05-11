from fastapi import APIRouter
from app.schemas.schemas import BalanceResponse
from app.services.exchange_service import exchange_service

router = APIRouter()

@router.get("/", response_model=BalanceResponse)
def get_balance():
    balances = exchange_service.get_all_balances()
    return {"balances": balances}
