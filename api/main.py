from typing import Any, Optional

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel

ORIGINS = [
    "http://localhost:5173",  # LOCAL/DEV
]


class APIResponse(BaseModel):
    detail: str
    data: Optional[Any] = None


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", status_code=status.HTTP_200_OK)
def root() -> APIResponse:
    """Makes health check to API root URL."""
    return APIResponse(detail="Healthy!")


handler = Mangum(app)
