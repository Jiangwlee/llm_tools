from fastapi import FastAPI
from src.llm_tools_v1.api.v1.helloworld import router as helloworld_router
from src.llm_tools_v1.api.v1.biddingcsg import router as biddingcsg_router

app = FastAPI()
app.include_router(helloworld_router, prefix="/api/v1")
app.include_router(biddingcsg_router, prefix="/api/v1") 