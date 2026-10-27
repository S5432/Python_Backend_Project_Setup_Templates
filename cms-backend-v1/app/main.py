from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return{
        "message": "Welcome to cms_backend_template version 1"
    }