from collections import defaultdict


STATES = ["ToDo", "Ongoing", "Blocked", "Done"]


def coalesce(*args):
    for arg in args:
        if arg is not None:
            return arg


class Component:
    sep = ""
    default = defaultdict(str)

    def __init__(self, *args, **kwargs):
        self.kwargs = defaultdict(
            str,
            {
                **{
                    f"_{i}": coalesce(arg, self.default[i])
                    for i, arg in enumerate(args)
                },
                **{k: coalesce(v, self.default[k]) for k, v in kwargs.items()},
            },
        )

    def __repr__(self):
        parts = []
        for k, v in self.kwargs.items():
            parts.append(f"{k}={v!r}")
        return (
            f"""<{self.__class__.__name__}{f" {' '.join(parts)}" if parts else ""}>"""
        )

    def __str__(self):
        t_kwargs = {}
        for slot, value in self.kwargs.items():
            if isinstance(value, list):
                t_kwargs[slot] = self.sep.join(str(element) for element in value)
            else:
                t_kwargs[slot] = str(value)
        return self.__doc__.format_map(defaultdict(str, t_kwargs))


class Kanban(Component):
    """
    <h2>Current sprint
        <button hx-post="/finish-sprint" hx-select="body" hx-target="body" hx-replace="outerHTML" hx-confirm="Are you sure you want to close the sprint?">Finish sprint</button>
        <button hx-get="/tasks/new?selected=checked" hx-target="#popoverholder">New selected task</button>
    </h2>
    <article>
    {columns}
    </article>
    """


class Subtasks(Component):
    """
    <h4>Subtasks</h4>
    {_0}
    <hr>
    """


class KanbanColumns(Component):
    """
    {parent_task}
    <div hx-ext="drag" class="grid kanban">
      {_0}
    </div>
    """


class UserChoice(Component):
    """
    <div class="user-card">
      <img class="avatar" src="{avatar}">
      <a href="/login-as/{id}"><strong>{name}</strong></a><br>
    </div>
    """


class UserChoices(Component):
    """
    <dialog open closedby="any">
    <div class="login-selection">
    <article class="user-card">
    <header>
    <h4>Choose user</h4>
    </header>
    {_0}
      <a href="/users/new">+ New user</a><br>
    </article>
    </div>
    </dialog>
    """


class Backlog(Component):
    """
    <h2>Backlog <small>({n_items})</small></h2>
    <article class="backlog">
      {items}
    </article>
    """


class NoTasksPlaceholder(Component):
    """
    <div class="no-tasks-placeholder">
      (No tasks here)
    </div>
    """


class KanbanColumn(Component):
    """
    <div class="kanban-col kanban-col-{name}">
      {heading}
      <div class="kanban-col-items" hx-drop='{{"state": "{name}"}}' hx-drop-action="/tasks/state">
        {items}
      </div>
    </div>
    """


class TaskCard(Component):
    """
    <article class="task-card" hx-drag='{{"task": "{id}"}}' draggable="{draggable}">
      {buttons}
      <a href="/tasks/{id}"><span class="id">{id}</span> <strong>{summary}</strong></a><br>
      <small>{details}</small>
    </article>
    """

    @classmethod
    def from_row(cls, row, with_select_button=False, draggable=False):
        details = [
            User.from_task(row),
            Storypoints(row["storypoints_sum"] + row["storypoints"]),
        ]
        if row["n_subtasks"]:
            details.append(f"{row['n_subtasks']} subtasks")
        if row["n_comments"]:
            details.append(f"{row['n_comments']} 💬")
        data = {
            "id": row["id"],
            "summary": row["summary"],
            "details": details,
        }
        if with_select_button:
            data["buttons"] = SelectButton(id=row["id"])
        data["draggable"] = str(draggable).lower()
        return cls(**data)

    sep = " · "


class TaskRow(Component):
    """
    <article class="task-card task-row">
      <a href="/tasks/{id}"><span class="id">{id}</span> <strong>{summary}</strong></a>
      <small>{details}</small>
      {items}
    </article>
    """

    @classmethod
    def from_row(cls, row, items):
        details = [
            User.from_task(row),
            Storypoints(row["storypoints_sum"] + row["storypoints"]),
        ]
        if row["n_subtasks"]:
            details.append(f"{row['n_subtasks']} subtasks")
        if row["n_comments"]:
            details.append(f"{row['n_comments']} 💬")
        data = {
            "id": row["id"],
            "summary": row["summary"],
            "details": details,
            "items": items,
        }
        return cls(**data)

    sep = " · "


class SelectButton(Component):
    """<button hx-post="/tasks/{id}/select">Select</button>"""


class TaskDetail(Component):
    """
    <div class="task-view split-view">
    <article class="main">
    <header>
        <div role="group">
            <button hx-get="/tasks/new?parent_task_id={id}" hx-target="#popoverholder">New subtask</button>
            <button hx-get="/tasks/{id}/edit" hx-target="#popoverholder">Edit</button>
        </div>
        <h3><span class="id">{id}</span> <strong>{title}</strong></h3>
    </header>
    {description}
    <footer>
    {subtasks}
    {comments}
    <form hx-post="/tasks/{id}/comments">
    <input
        placeholder="Add a new comment..."
        name="comment"
        autocomplete="off"
    >
    </form>
    </footer>
    </article>
    <div class="sidebar">
    {properties}
    </div>
    </div>
    """


class TaskProperty(Component):
    """
    <p><strong>{_0}:</strong> {_1}</p>
    """


class Widget(Component):
    """
    <!DOCTYPE html>
    <html data-theme="light">
    <head>
        <title>{title}</title>
        <link rel="stylesheet" href="/style.css">
        <link rel="stylesheet" href="/pico.min.css">
    </head>
    <body class="fluid-container">
        {body}
    </body>
    </html>
    """


class LoggedOutPage(Component):
    """
    <!DOCTYPE html>
    <html data-theme="light">
    <head>
        <script src="/htmx.js"></script>
        <script src="/hx-drag.js"></script>
        <title>{title}</title>
        <link rel="stylesheet" href="/style.css">
        <link rel="stylesheet" href="/pico.min.css">
    </head>
    <body class="container">
        <div id="popoverholder"></div>
        <nav>
            <ul>
                <li>zutun</li>
                <li><a href="/">Board</a></li>
                <li><a href="/backlog">Backlog</a></li>
            </ul>
            <ul>
                <li><button hx-get="/tasks/new" hx-target="#popoverholder">New task</button></li>
                <li><input type="search"></li>
                <!- LOGOUT -->
            </ul>
        </nav>
        <main>
            {body}
        </main>
    </body>
    </html>
    """


class Page(Component): ...


Page.__doc__ = LoggedOutPage.__doc__.replace(
    "<!- LOGOUT -->",
    """
    <li>{logout}</li>
""",
)


class Dialog(Component):
    """
    <dialog open closedby="any">
    <article>
    <header>
    <button hx-get="/blank" hx-target="#popoverholder">X</button>
    <h4>{title}</h4>
    </header>
    {content}
    </article>
    </dialog>
    """


class UserForm(Component):
    """
    <article>
    <header>
    <h4>New user</h4>
    </header>
    <form
        enctype="multipart/form-data"
        hx-post="{endpoint}"
    >
    <fieldset>
    <label>
        Name
        <input
            name="name"
            placeholder="Name"
            autocomplete="off"
            value="{name}"
        >
    </label>
    <label>
        Avatar
        <input name="avatar" type="file"></input>
    </label>
    </fieldset>
    <input
        type="submit"
        value="Submit"
    >
    </form>
    </article>
    """


class AssigneeChoice(Component):
    """
    <option value="{id}" {selected}>{name}</option>
    """


class TaskForm(Component):
    """
    <form hx-post="{endpoint}">
    <fieldset>
    <label>
        Summary
        <input
            name="summary"
            placeholder="Task summary"
            autocomplete="off"
            value="{summary}"
        >
    </label>
    <label>
        Description
        <textarea
            name="description"
            placeholder="Longer description..."
            autocomplete="off"
        >{description}</textarea>
    </label>
    <label>
        Assignee
        <select name="assignee_id">
          <option value=""><em>Unassigned</em></option>
          {assignee_choices}
        </select>
    </label>
    <label>
        Storypoints
        <input
            name="storypoints"
            placeholder="0"
            autocomplete="off"
            value="{storypoints}"
            type="numeric"
        >
    </label>
    <label for="parent_task_id">
        Parent task
        <fieldset role="group">
        <input value="#" class="input-prefix" disabled>
        <input
            id="parent_task_id"
            name="parent_task_id"
            placeholder="0"
            autocomplete="off"
            value="{parent_task_id}"
            type="numeric"
        >
        </fieldset>
    </label>
    <label for="selected">
        <input id="selected" name="selected" type="checkbox" role="switch" {selected}/>
        Selected
    </fieldset>
    <input
        type="submit"
        value="Submit"
    >
    </form>
    """


class Storypoints(Component):
    """<span class="storypoints">{_0}</span>"""

    default = {0: " – "}


class User(Component):
    """<span class="user {user_set}"><img class="avatar" src="{avatar}">{name}</span>"""

    default = {"name": "<em>unassigned</em>", "avatar": "", "user_set": ""}

    @classmethod
    def from_task(cls, task):
        return cls(
            name=task["assignee_name"],
            avatar=task["assignee_avatar"],
            user_set="user-set" if task["assignee_id"] else "",
        )

    @classmethod
    def from_comment(cls, comment):
        return cls(
            name=comment["commenter_name"] or "<em>anonymous</em>",
            avatar=comment["commenter_avatar"],
            user_set="user-set" if comment["commenter_id"] else "",
        )


class Description(Component):
    """<span class="description">{_0}</span>"""

    default = {0: "<em>(no description)</em>"}


class StateSelector(Component):
    """
    <form>
    <input type="hidden" name="task" value="{task_id}">
    <select name="state" hx-put="/tasks/state">
        {options}
    </select>
    </form>
    """

    @classmethod
    def from_task(cls, task):
        return cls(
            task_id=task["id"],
            options=[
                StateOption(
                    state=state,
                    selected="selected" if state == task["state"] else "",
                )
                for state in STATES
            ],
        )


class StateOption(Component):
    """<option {selected}>{state}</option>"""


class Comment(Component):
    """
    <div class="comment">
    {commenter} wrote <em data-tooltip="{created_at}">{created_at_human}</em>:
    <span class="comment-text">{text}</comment>
    </div><hr>
    """


class TaskLink(Component):
    """
    <a href="/tasks/{id}" class="task-link"><span class="id">{id}</span> {summary}</a>
    """


class LogoutBar(Component):
    """
    <details class="dropdown"><summary><img class="avatar" src="{avatar}">{name}</summary>
    <ul><li><a href="/login">Logout</a></li></ul></details>
    """
