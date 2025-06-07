from fastapi import FastAPI
from src.llm_tools_v1.api.v1.helloworld import router as helloworld_router

app = FastAPI()
app.include_router(helloworld_router, prefix="/api/v1") 