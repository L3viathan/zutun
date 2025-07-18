import re
import os
import base64
from io import BytesIO
from datetime import datetime

from PIL import Image
from humanize import naturaltime
from sanic import Sanic
from sanic.response import html, file, redirect, HTTPResponse

from zutun.components import *
from zutun.db import conn


app = Sanic("zutun")


CORRECT_AUTH = os.environ["ZUTUN_CREDS"]
TASK_QUERY = """
    SELECT
        tasks.id AS id,
        tasks.summary AS summary,
        tasks.description AS description,
        tasks.location AS location,
        tasks.state AS state,
        tasks.parent_task_id AS parent_task_id,
        u.id AS assignee_id,
        u.name AS assignee_name,
        u.avatar AS assignee_avatar,
        tasks.assignee_id AS assignee,
        COALESCE(tasks.storypoints, 0) AS storypoints,
        COUNT(subtask.id) AS n_subtasks,
        COUNT(c.id) AS n_comments,
        SUM(subtask.state <> 'Done') AS n_incomplete_subtasks,
        COALESCE(SUM(subtask.storypoints), 0) AS storypoints_sum
    FROM tasks
    LEFT OUTER JOIN tasks subtask ON subtask.parent_task_id = tasks.id
    LEFT JOIN users u ON tasks.assignee_id = u.id
    LEFT OUTER JOIN comments c ON c.task_id = tasks.id
    WHERE
        {conditions}
    GROUP BY tasks.id
    ORDER BY n_incomplete_subtasks ASC
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
                max_age=60 * 60 * 24 * 365,  # roughly one year
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


@app.on_request
async def check_login(request):
    if hasattr(request.route.handler, "_ignore_login_check"):
        return
    user = request.cookies.get("user")
    if not user:
        return redirect("/login")


def allow_logged_out(fn):
    fn._ignore_login_check = True
    return fn


@app.get("/login-as/<user>")
@allow_logged_out
async def login_as(request, user):
    response = redirect("/")
    response.add_cookie(
        "user",
        user,
        secure=True,
        httponly=True,
        samesite="Strict",
        max_age=60 * 60 * 24 * 365,  # roughly one year
    )
    return response


TASK_PATTERN = re.compile(r"#(\d+)\b")
USER_PATTERN = re.compile(r"@(\d+)\b")


def D(multival_dict):
    return {key: val[0] for key, val in multival_dict.items()}


def scale_image(img, target_size):
    """
    Scale image to a fixed, square size.

    When the original image isn't a square, take only the central, square
    portion.
    """
    max_size = max(img.size)
    min_size = min(img.size)
    x, y = img.size
    x_diff, y_diff = (max_size - x) // 2, (max_size - y) // 2
    return img.resize(
        (
            target_size,
            target_size,
        ),
        box=(
            0 + y_diff,
            0 + x_diff,
            min_size + y_diff,
            min_size + x_diff,
        ),
    )


def _kanban_columns_from_tasks(tasks, parent_task=None):
    columns = {state: [] for state in STATES}
    storypoints = {state: 0 for state in STATES}
    for task in tasks:
        columns[task["state"]].append(
            TaskCard.from_row(task, draggable=True),
        )
        storypoints[task["state"]] += task["storypoints_sum"] or task["storypoints"]
    result = KanbanColumns(
        [
            KanbanColumn(
                name=state,
                heading=f"<h4>{state} <small>({storypoints[state]})</small></h4><hr>",
                items=columns[state] or NoTasksPlaceholder(),
            )
            for state in STATES
        ],
    )
    if parent_task:
        result = TaskRow.from_row(parent_task, items=result)
    return result


def _kanban_board_from_tasks(tasks):
    parent_task_ids = [task["id"] for task in tasks if task["n_incomplete_subtasks"]]
    if parent_task_ids:
        subtasks = conn.execute(
            TASK_QUERY.format(
                conditions=f"""
                    tasks.parent_task_id IN ({",".join("?" * len(parent_task_ids))})
                """,
            ),
            parent_task_ids,
        ).fetchall()
    else:
        subtasks = None

    rows = [
        _kanban_columns_from_tasks(
            [task for task in tasks if not task["n_incomplete_subtasks"]]
        )
    ]
    for task in tasks:
        if task["n_incomplete_subtasks"]:
            rows.append(
                _kanban_columns_from_tasks(
                    [
                        subtask
                        for subtask in subtasks
                        if subtask["parent_task_id"] == task["id"]
                    ],
                    parent_task=task,
                )
            )
    return rows


@app.get("/")
async def board(request):
    user = conn.execute(
        "SELECT * FROM users WHERE id=?", (int(request.cookies.get("user")),)
    ).fetchone()

    tasks = conn.execute(
        TASK_QUERY.format(
            conditions="""
                tasks.location = 'selected'
                AND tasks.parent_task_id IS NULL
            """
        ),
    ).fetchall()
    page = Page(
        title="zutun — Board",
        body=Kanban(columns=_kanban_board_from_tasks(tasks)),
        logout=LogoutBar(**user),
    )
    return html(str(page))


@app.get("/login")
@allow_logged_out
async def login(request):
    items = []
    for row in conn.execute("SELECT * FROM users").fetchall():
        items.append(UserChoice(**row))
    page = LoggedOutPage(
        title="zutun — Login",
        body=UserChoices(
            items,
        ),
    )
    return html(str(page))


@app.get("/backlog")
async def backlog(request):
    items = []
    for i, t in enumerate(
        conn.execute(
            TASK_QUERY.format(
                conditions="""
                    tasks.location = 'backlog' AND tasks.parent_task_id IS NULL
                """
            ),
        ).fetchall()
    ):
        items.append(
            TaskCard.from_row(
                t,
                with_select_button=True,
            )
        )
    user = conn.execute(
        "SELECT * FROM users WHERE id=?", (int(request.cookies.get("user")),)
    ).fetchone()
    page = Page(
        title="zutun — Backlog",
        body=Backlog(
            n_items=len(items),
            items=items or NoTasksPlaceholder(),
        ),
        logout=LogoutBar(**user),
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
    task = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (int(match.group(1)),)
    ).fetchone()
    return str(TaskLink(**task))


def _replace_user_ref(match):
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (int(match.group(1)),)
    ).fetchone()
    return str(
        User(
            user_set="user-set",
            name=user["name"],
            avatar=user["avatar"],
        )
    )


def replace_task_references(text):
    if not text:
        return text
    return USER_PATTERN.sub(
        _replace_user_ref, TASK_PATTERN.sub(_replace_task_ref, text)
    )


@app.get("/tasks/<task_id>")
async def view_task(request, task_id: int):
    task = conn.execute(
        TASK_QUERY.format(conditions="tasks.id = ?"), (task_id,)
    ).fetchone()
    comments = conn.execute(
        """
        SELECT
            comments.id AS id,
            comments.task_id AS task_id,
            comments.text AS text,
            comments.created_at AS created_at,
            u.id AS commenter_id,
            u.name AS commenter_name,
            u.avatar AS commenter_avatar
        FROM comments
        LEFT JOIN users u ON comments.commenter_id = u.id
        WHERE task_id = ?
    """,
        (task_id,),
    ).fetchall()
    subtasks = conn.execute(
        TASK_QUERY.format(
            conditions="""
                tasks.parent_task_id = ?
            """
        ),
        (task_id,),
    ).fetchall()
    user = conn.execute(
        "SELECT * FROM users WHERE id=?", (int(request.cookies.get("user")),)
    ).fetchone()
    if not task:
        return redirect("/")
    props = [StateSelector.from_task(task)]
    if not task["parent_task_id"]:
        props.append(TaskProperty("Location", task["location"]))
    if task["assignee_id"]:
        props.append(TaskProperty("Assignee", User.from_task(task)))
    if task["storypoints"]:
        props.append(TaskProperty("Storypoints", Storypoints(task["storypoints"])))
    if task["parent_task_id"]:
        props.append(
            TaskProperty(
                "Parent task", replace_task_references(f"#{task['parent_task_id']}")
            )
        )
    page = Page(
        title=f"{task['id']} - {task['summary']}",
        body=TaskDetail(
            id=task["id"],
            title=task["summary"],
            description=Description(replace_task_references(task["description"])),
            properties=props,
            comments=[
                Comment(
                    commenter=User.from_comment(comment),
                    created_at=comment["created_at"],
                    created_at_human=naturaltime(
                        datetime.fromisoformat(comment["created_at"])
                    ),
                    text=replace_task_references(comment["text"]),
                )
                for comment in comments
            ],
            subtasks=Subtasks(_kanban_board_from_tasks(subtasks)) if subtasks else None,
        ),
        logout=LogoutBar(**user),
    )
    return html(str(page))


@app.get("/users/new")
@allow_logged_out
async def new_user_form(request):
    return html(
        str(
            LoggedOutPage(
                title="New user",
                body=UserForm(
                    endpoint="/users/new",
                ),
            )
        )
    )


@app.post("/users/new")
@allow_logged_out
async def new_user(request):
    data = D(request.form)
    f = request.files["avatar"][0]
    img = scale_image(Image.open(BytesIO(f.body)), 128)
    io = BytesIO()
    img.save(io, format="JPEG")
    conn.execute(
        "INSERT INTO users (name, avatar) VALUES (?, ?)",
        (data["name"], f"data:jpg;base64,{base64.b64encode(io.getvalue()).decode()}"),
    )
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


@app.get("/tasks/new")
async def new_task_form(request):
    args = D(request.args)
    users = conn.execute("SELECT id, name, avatar FROM users").fetchall()
    return html(
        str(
            Dialog(
                title="New task",
                content=TaskForm(
                    endpoint="/tasks/new",
                    selected=args.get("selected"),
                    parent_task_id=args.get("parent_task_id"),
                    assignee_choices=[AssigneeChoice(**user) for user in users],
                ),
            )
        )
    )


@app.get("/tasks/<task_id>/edit")
async def edit_task_form(request, task_id: int):
    task = conn.execute(
        TASK_QUERY.format(conditions="tasks.id = ?"), (task_id,)
    ).fetchone()
    users = conn.execute("SELECT id, name, avatar FROM users").fetchall()
    return html(
        str(
            Dialog(
                title="Edit task",
                content=TaskForm(
                    endpoint=f"/tasks/{task_id}/edit",
                    assignee_choices=[
                        AssigneeChoice(
                            selected="selected"
                            if user["id"] == task["assignee_id"]
                            else "",
                            **user,
                        )
                        for user in users
                    ],
                    **task,
                ),
            )
        )
    )


@app.post("/tasks/<task_id>/comments")
async def post_comment(request, task_id: int):
    user_id = int(request.cookies.get("user"))
    data = D(request.form)
    conn.execute(
        "INSERT INTO comments (task_id, text, commenter_id) VALUES (?, ?, ?)",
        (
            task_id,
            data["comment"],
            user_id,
        ),
    )
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


@app.post("/tasks/<task_id>/edit")
async def edit_task(request, task_id: int):
    data = D(request.form)
    conn.execute(
        "UPDATE tasks SET summary=?, description=?, assignee_id=?, storypoints=?, parent_task_id=? WHERE id=?",
        (
            data["summary"],
            data.get("description"),
            data.get("assignee_id") or None,
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
    cur.execute(
        "UPDATE tasks SET location='graveyard' WHERE location = 'selected' AND state = 'Done'"
    )
    cur.execute(
        "UPDATE tasks SET location='backlog' WHERE location = 'selected' AND state <> 'Done'"
    )
    conn.commit()
    return html("", headers={"HX-Location": "/backlog"})


@app.post("/tasks/new")
async def new_task(request):
    data = D(request.form)
    conn.execute(
        "INSERT INTO tasks (summary, description, assignee_id, storypoints, parent_task_id, state, location) VALUES (?, ?, ?, ?, ?, 'ToDo', ?)",
        (
            data["summary"],
            data.get("description"),
            data.get("assignee_id") or None,
            data.get("storypoints"),
            data.get("parent_task_id"),
            "selected" if data.get("selected") else "backlog",
        ),
    )
    conn.commit()
    return html("", headers={"HX-Refresh": "true"})


@app.get("/blank")
async def blank(request):
    return html("")


@app.get("/pico.min.css")
@allow_logged_out
async def pico_css(request):
    return await file("pico.min.css", mime_type="text/css")


@app.get("/style.css")
@allow_logged_out
async def style_css(request):
    return await file("style.css", mime_type="text/css")


@app.get("/htmx.js")
@allow_logged_out
async def htmx_js(request):
    return await file("htmx.js", mime_type="text/javascript")


@app.get("/hx-drag.js")
@allow_logged_out
async def hx_drag_js(request):
    return await file("hx-drag.js", mime_type="text/javascript")
