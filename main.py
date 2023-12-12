from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from gmail_service import fetch_gmail_messages

app = FastAPI()

# Serve static files (CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Sample data
mail_data = {
    "mails": [
        {
            "id": "123",
            "summary": "this is a test message",
            "full_msg": "this is a test message",
            "from": "abc@abc.com",
            "categories": ["test", "test2", "test3"],
            "labels": ["label1", "label2", "label3"],
            "subject": "This is a subject",
        }
        # Add more mail entries if needed
    ]
}


@app.on_event("startup")
def fetch_messages():
    global mail_data
    mail_data = fetch_gmail_messages()


# Routes
@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "mails": mail_data["mails"]})


@app.get("/mail/{mail_id}")
def read_mail(mail_id: str, request: Request):
    mail = next((m for m in mail_data["mails"] if m["id"] == mail_id), None)
    if mail:
        return templates.TemplateResponse("mail.html", {"request": request, "mail": mail})
    else:
        raise HTTPException(status_code=404, detail="Mail not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
