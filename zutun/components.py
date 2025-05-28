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
                **{f"_{i}": coalesce(arg, self.default[i]) for i, arg in enumerate(args)},
                 **{k: coalesce(v, self.default[k]) for k, v in kwargs.items()}
            },
        )

    def __repr__(self):
        parts = []
        for k, v in self.kwargs.items():
            parts.append(f"{k}={v!r}")
        return f"""<{self.__class__.__name__}{
            f' {" ".join(parts)}'
            if parts
            else ''
            }>"""

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
    <div hx-ext="drag" class="grid kanban">
      {_0}
    </div>
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
      <h4>{name} <small>({total})</small></h4>
      <hr>
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
            Assignee(row["assignee"]),
            Storypoints(row["storypoints_sum"] + row["storypoints"]),
        ]
        if row["n_subtasks"]:
            details.append(f"{row['n_subtasks']} subtasks")
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


class Page(Component):
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
            </ul>
        </nav>
        <main>
            {body}
        </main>
    </body>
    </html>
    """


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
        <input
            name="assignee"
            placeholder="Someone"
            autocomplete="off"
            value="{assignee}"
        >
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


class Assignee(Component):
    """<span class="assignee">{_0}</span>"""

    default = {0: "<em>unassigned</em>"}


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
    <em>{created_at}</em>: {text}
    </div><hr>
    """


class TaskLink(Component):
    """
    <a href="/tasks/{id}" class="task-link"><span class="id">{id}</span> {summary}</a>
    """
