from importlib.resources import files
from sanic import Sanic
from sanic.response import html, file, redirect

from zutun.components import *


app = Sanic("zutun")

tickets = {
    i: {"number": i, "assignee": "Jonathan", "storypoints":i % 4, "title":f"Foo bar ({i})", "state": "ToDo"}
    for i in range(10)
}

def _tickets_in_state(state):
    return [
        TicketCard(title=t["title"], details=[t["assignee"], t["storypoints"]], number=t["number"])
        for t in tickets.values()
        if t["state"] == state
    ]

def _all_tickets():
    return [
        TicketCard(title=t["title"], details=[t["assignee"], t["storypoints"], t["state"]], number=t["number"])
        for t in tickets.values()
    ]


@app.get("/")
async def board(request):
    page = Page(
        title="zutun — Board",
        body=Kanban(
            columns=[
                KanbanColumn(name=state, items=_tickets_in_state(state))
                for state in ["ToDo", "Ongoing", "Blocked", "Done"]
            ],
        ),
    )
    return html(str(page))


@app.get("/backlog")
async def backlog(request):
    page = Page(
        title="zutun — Backlog",
        body=Backlog(
            items=_all_tickets(),
        ),
    )
    return html(str(page))


@app.put("/ticket/<ticket_id>/state")
async def change_state(request, ticket_id: int):
    tickets[ticket_id]["state"] = request.form["state"][0]
    return html("", headers={"HX-Refresh": "true"})


@app.get("/pico.min.css")
async def pico_css(request):
    return await file("pico.min.css", mime_type="text/css")


@app.get("/style.css")
async def style_css(request):
    return await file("style.css", mime_type="text/css")


@app.get("/htmx.js")
async def htmx_js(request):
    return await file("htmx.js", mime_type="text/javascript")


@app.get("/hx-drag.js")
async def hx_drag_js(request):
    return await file("hx-drag.js", mime_type="text/javascript")
