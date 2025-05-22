from importlib.resources import files
from sanic import Sanic
from sanic.response import html, file, redirect

from zutun.components import *
from zutun.db import conn


app = Sanic("zutun")

def D(multival_dict):
    return {key: val[0] for key, val in multival_dict.items()}

@app.get("/")
async def board(request):
    page = Page(
        title="zutun — Board",
        body=Kanban(
            columns=[
                KanbanColumn(
                    name=state,
                    items=[
                        TicketCard.from_row(row, draggable=True)
                        for row in conn.execute(
                            "SELECT * FROM tasks WHERE state = ?",
                            (state,),
                        ).fetchall()
                    ] or NoTicketsPlaceholder(),
                )
                for state in ["ToDo", "Ongoing", "Blocked", "Done"]
            ],
        ),
    )
    return html(str(page))


@app.get("/backlog")
async def backlog(request):
    items = []
    for i, t in enumerate(conn.execute("SELECT * FROM tasks WHERE state IS NULL").fetchall()):
        items.append(TicketCard.from_row(
            t,
            with_select_button=True,
        ))
    page = Page(
        title="zutun — Backlog",
        body=Backlog(
            items=items or NoTicketsPlaceholder(),
        ),
    )
    return html(str(page))


@app.put("/tickets/state")
async def change_state(request):
    data = D(request.form)
    ticket_id = int(data["ticket"])
    conn.execute("UPDATE tasks SET state=? WHERE id=?", (data["state"], ticket_id))
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


@app.post("/tickets/<ticket_id>/select")
async def select_ticket(request, ticket_id: int):
    conn.execute("UPDATE tasks SET state=? WHERE id=?", ("ToDo", ticket_id))
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


@app.get("/tickets/<ticket_id>")
async def view_ticket(request, ticket_id: int):
    ticket = conn.execute("SELECT * FROM tasks WHERE id = ?", (ticket_id,)).fetchone()
    if not ticket:
        return redirect("/")
    props = []
    if ticket["assignee"]:
        props.append(TicketProperty("Assignee", ticket["assignee"]))
    if ticket["storypoints"]:
        props.append(TicketProperty("Storypoints", Storypoints(ticket["storypoints"])))
    if ticket["state"]:
        props.append(TicketProperty("State", ticket["state"]))
    page = Page(
        title=f"{ticket['id']} - {ticket['summary']}",
        body=TicketDetail(
            id=ticket["id"],
            title=ticket["summary"],
            summary=ticket["description"],
            properties=props,
        ),
    )
    return html(str(page))


@app.get("/tickets/new")
async def new_ticket_form(request):
    return html(str(Dialog(
        title="New ticket",
        content=TicketForm(endpoint="/tickets/new"),
    )))


@app.get("/tickets/<ticket_id>/edit")
async def edit_ticket_form(request, ticket_id: int):
    ticket = conn.execute("SELECT * FROM tasks WHERE id = ?", (ticket_id,)).fetchone()
    return html(str(Dialog(
        title="Edit ticket",
        content=TicketForm(
            endpoint=f"/tickets/{ticket_id}/edit",
            **ticket,
        ),
    )))


@app.post("/tickets/<ticket_id>/edit")
async def edit_ticket(request, ticket_id: int):
    data = D(request.form)
    conn.execute(
        "UPDATE tasks SET summary=?, description=?, assignee=?, storypoints=? WHERE id=?",
        (
            data["summary"],
            data.get("description"),
            data.get("assignee"),
            data.get("storypoints"),
            ticket_id,
        ),
    )
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


@app.post("/finish-sprint")
async def finish_sprint(request):
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET state='Closed' WHERE state = 'Done'")
    cur.execute("UPDATE tasks SET state=NULL WHERE state IS NOT NULL AND state <> 'Closed'")
    conn.commit()
    return html("", headers={"HX-Location": "/backlog"})


@app.post("/tickets/new")
async def new_ticket(request):
    data = D(request.form)
    conn.execute(
        "INSERT INTO tasks (summary, description, assignee, storypoints) VALUES (?, ?, ?, ?)",
        (
            data["summary"],
            data.get("description"),
            data.get("assignee"),
            data.get("storypoints"),
        ),
    )
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


@app.get("/blank")
async def blank(request):
    return html("")


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
