import re
import os
import base64
from io import BytesIO
from importlib.resources import files

from PIL import Image, ImageDraw
from sanic import Sanic
from sanic.response import html, file, redirect, HTTPResponse, raw

from zutun.components import *
from zutun.db import conn


app = Sanic("zutun")


CORRECT_AUTH = os.environ["ZUTUN_CREDS"]
TASK_QUERY = """
    SELECT *, COUNT(subtask.id) AS n_subtasks
    FROM tasks
    LEFT OUTER JOIN tasks subtask ON subtask.parent_task_id = tasks.id
    WHERE
        {conditions}
    GROUP BY tasks.id
"""

@app.on_request
async def auth(request):
    cookie = request.cookies.get("auth")
    if cookie == CORRECT_AUTH:
        return
    try:
        auth = request.headers["Authorization"]
        _, _, encoded = auth.partition(" ")
        if base64.b64decode(encoded).decode() == CORRECT_AUTH:
            response = redirect("/")
            response.add_cookie(
                "auth",
                CORRECT_AUTH,
                secure=True,
                httponly=True,
                    samesite="Strict",
                    max_age=60*60*24*365,  # roughly one year
            )
            return response
        else:
            raise ValueError
    except (KeyError, AssertionError, ValueError):
        return HTTPResponse(
            body="401 Unauthorized",
            status=401,
            headers={"WWW-Authenticate": 'Basic realm="Zutun access"'},
        )

REF_PATTERN = re.compile(r"#(\d+)\b")

def D(multival_dict):
    return {key: val[0] for key, val in multival_dict.items()}


@app.get("/widget/<states>")
async def widget(request, states):
    states = states.split(",")
    conds = " OR ".join("state = ?" for _ in range(len(states)))
    tasks = conn.execute(
        f"SELECT * FROM tasks WHERE {conds}",
        tuple(states),
    ).fetchall()
    img = Image.new("RGBA", (600, 800), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw.multiline_text((10, 10), "\n".join(
        row["summary"] for row in tasks
    ), font_size=48, fill="black")
    io = BytesIO()
    img.save(io, format="png", mode="RGBA")
    return raw(io.getvalue(), content_type="image/png")


def _kanban_columns_from_tasks(tasks):
    columns = {
        state: [] for state in STATES
    }
    storypoints = {
        state: 0 for state in STATES
    }
    for task in tasks:
        columns[task["state"]].append(
            TaskCard.from_row(task, draggable=True),
        )
        storypoints[task["state"]] += task["storypoints"] or 0
    return KanbanColumns([
        KanbanColumn(
            name=state,
            items=columns[state] or NoTasksPlaceholder(),
            total=storypoints[state],
        )
        for state in STATES
    ])


@app.get("/")
async def board(request):
    columns = []
    tasks = conn.execute(
        TASK_QUERY.format(conditions="""
            tasks.location = 'selected'
            AND tasks.parent_task_id IS NULL
        """),
    ).fetchall()
    page = Page(
        title="zutun — Board",
        body=Kanban(columns=_kanban_columns_from_tasks(tasks)),
    )
    return html(str(page))


@app.get("/backlog")
async def backlog(request):
    items = []
    for i, t in enumerate(conn.execute(
        TASK_QUERY.format(conditions=
            """
            tasks.location = 'backlog' AND tasks.parent_task_id IS NULL
        """),
    ).fetchall()):
        items.append(TaskCard.from_row(
            t,
            with_select_button=True,
        ))
    page = Page(
        title="zutun — Backlog",
        body=Backlog(
            n_items=len(items),
            items=items or NoTasksPlaceholder(),
        ),
    )
    return html(str(page))


@app.put("/tasks/state")
async def change_state(request):
    data = D(request.form)
    task_id = int(data["task"])
    conn.execute("UPDATE tasks SET state=? WHERE id=?", (data["state"], task_id))
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


@app.post("/tasks/<task_id>/select")
async def select_task(request, task_id: int):
    conn.execute("UPDATE tasks SET location='selected' WHERE id=?", (task_id,))
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


def _replace_task_ref(match):
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (int(match.group(1)),)).fetchone()
    return str(TaskLink(**task))


def replace_task_references(text):
    if not text:
        return text
    return REF_PATTERN.sub(_replace_task_ref, text)


@app.get("/tasks/<task_id>")
async def view_task(request, task_id: int):
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    comments = conn.execute("SELECT * FROM comments WHERE task_id = ?", (task_id,)).fetchall()
    subtasks = conn.execute(
        TASK_QUERY.format(conditions="""
            tasks.parent_task_id = ?
        """),
        (task_id,),
    ).fetchall()
    if not task:
        return redirect("/")
    props = [StateSelector.from_task(task)]
    if not task["parent_task_id"]:
        props.append(TaskProperty("Location", task["location"]))
    if task["assignee"]:
        props.append(TaskProperty("Assignee", task["assignee"]))
    if task["storypoints"]:
        props.append(TaskProperty("Storypoints", Storypoints(task["storypoints"])))
    if task["parent_task_id"]:
        props.append(TaskProperty("Parent task", replace_task_references(f"#{task['parent_task_id']}")))
    page = Page(
        title=f"{task['id']} - {task['summary']}",
        body=TaskDetail(
            id=task["id"],
            title=task["summary"],
            description=Description(replace_task_references(task["description"])),
            properties=props,
            comments=[Comment(
                created_at=comment["created_at"],
                text=replace_task_references(comment["text"]),
            ) for comment in comments],
            subtasks=Subtasks(_kanban_columns_from_tasks(subtasks)) if subtasks else None,
        ),
    )
    return html(str(page))


@app.get("/tasks/new")
async def new_task_form(request):
    args = D(request.args)
    return html(str(Dialog(
        title="New task",
        content=TaskForm(
            endpoint="/tasks/new",
            parent_task_id=args.get("parent_task_id"),
        ),
    )))


@app.get("/tasks/<task_id>/edit")
async def edit_task_form(request, task_id: int):
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return html(str(Dialog(
        title="Edit task",
        content=TaskForm(
            endpoint=f"/tasks/{task_id}/edit",
            **task,
        ),
    )))


@app.post("/tasks/<task_id>/comments")
async def post_comment(request, task_id: int):
    data = D(request.form)
    conn.execute(
        "INSERT INTO comments (task_id, text) VALUES (?, ?)",
        (
            task_id,
            data["comment"],
        ),
    )
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


@app.post("/tasks/<task_id>/edit")
async def edit_task(request, task_id: int):
    data = D(request.form)
    conn.execute(
        "UPDATE tasks SET summary=?, description=?, assignee=?, storypoints=?, parent_task_id=? WHERE id=?",
        (
            data["summary"],
            data.get("description"),
            data.get("assignee"),
            data.get("storypoints"),
            data.get("parent_task_id"),
            task_id,
        ),
    )
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


@app.post("/finish-sprint")
async def finish_sprint(request):
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET location='graveyard' WHERE location = 'selected' AND state = 'Done'")
    cur.execute("UPDATE tasks SET location='backlog' WHERE location = 'selected' AND state <> 'Closed'")
    conn.commit()
    return html("", headers={"HX-Location": "/backlog"})


@app.post("/tasks/new")
async def new_task(request):
    data = D(request.form)
    conn.execute(
        "INSERT INTO tasks (summary, description, assignee, storypoints, parent_task_id, state, location) VALUES (?, ?, ?, ?, ?, 'ToDo', 'backlog')",
        (
            data["summary"],
            data.get("description"),
            data.get("assignee"),
            data.get("storypoints"),
            data.get("parent_task_id"),
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
