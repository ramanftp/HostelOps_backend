
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

from sqlalchemy import inspect

from modules.owner.routes import router, auth_router
from modules.bill_payment.routes import router as bill_router
from modules.expenses.routes import router as expense_router
from core.database import SessionLocal

from core.config import DATABASE_URL


logger = logging.getLogger(__name__)

app = FastAPI(title="HostelOps API", version="1.0.0")




app.add_middleware(
    CORSMiddleware,
    allow_origins=[
       "*"
    ],
    allow_credentials=True,   # set True only if using cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return JSONResponse({
        "api_version": "1.0.0",
        "message": "HostelOps API is running"
    })


app.include_router(auth_router)
app.include_router(router)
app.include_router(bill_router)
app.include_router(expense_router)




