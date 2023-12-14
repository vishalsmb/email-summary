import temp
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from fastapi.responses import HTMLResponse
from mail_service import fetch_gmail_messages, fetch_local_messages, get_message_details, get_email_text, format_message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import mail_details_table as mdt

app = FastAPI()
scheduler = AsyncIOScheduler()

# Serve static files (CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Sample data
mail_data = [
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


@app.on_event("startup")
def fetch_messages():
    global mail_data
    mail_data = fetch_local_messages()
    # scheduler.start()


@scheduler.scheduled_job("cron", hour="10", minute="20")
async def fetch_emails():
    global mail_data
    fetch_gmail_messages()
    mail_data = fetch_local_messages()


# Routes
@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "mails": mail_data})


@app.get("/refreshMessages")
async def refresh_messages():
    global mail_data
    mail_data = fetch_local_messages()
    return True


@app.get("/mail/{mail_id}")
async def read_mail(mail_id: str, request: Request):
    mail = next((m for m in mail_data if m["id"] == mail_id), {})
    if len(mail) or not mail.get('full_msg'):
        message_details = get_message_details(mail_id)
        mail['full_msg'] = get_email_text(message_details)
        return templates.TemplateResponse("mail.html", {"request": request, "mail": mail})
    elif not mail:
        message_details = get_message_details(mail_id)
        new_message = format_message(mail_id, message_details)
        new_message["full_msg"] = get_email_text(message_details)
        return templates.TemplateResponse("mail.html", {"request": request, "mail": new_message})
    else:
        raise HTTPException(status_code=404, detail="Mail not found")


# Number of results per page
PAGE_SIZE = 10


@app.get("/get_list", response_class=HTMLResponse)
async def read_items(
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(PAGE_SIZE, le=100),
        mail_id: str = None,
        date: str = None,
        search: str = None
):
    response = mdt.fetch_paginated_records(request, page, per_page, mail_id, date, search)
    return templates.TemplateResponse(
        "mail_list.html",
        response
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
