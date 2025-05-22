from collections import defaultdict


class Component:
    sep = ""
    def __init__(self, **kwargs):
        self.kwargs = defaultdict(str, kwargs)

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
    <article hx-ext="drag" class="grid kanban">
      {columns}
    </article>
    """


class Backlog(Component):
    """
    <h2>Backlog</h2>
    <article class="backlog">
      {items}
    </article>
    """


class NoTicketsPlaceholder(Component):
    """
    <div class="no-tickets-placeholder">
      (No tickets here)
    </div>
    """


class PositionDropTarget(Component):
    """
    <hr hx-drop='{{"position": "{pos}"}}' hx-drop-action="/backlog/reorder">
    """


class KanbanColumn(Component):
    """
    <div class="kanban-col kanban-col-{name}">
      <h4>{name}</h4>
      <hr>
      <div class="kanban-col-items" hx-drop='{{"state": "{name}"}}' hx-drop-action="/tickets/state">
        {items}
      </div>
    </div>
    """


class TicketCard(Component):
    """
    <article class="ticket-card" hx-ext="drag" hx-drag='{{"ticket": "{id}"}}' draggable="true">
      {buttons}
      <a href="/tickets/{id}">{id} <strong>{summary}</strong></a><br>
      <small>{details}</small>
    </article>
    """

    @classmethod
    def from_row(cls, row, with_select_button=False):
        data = {
            "id": row["id"],
            "summary": row["summary"],
            "details": [row["assignee"], row["storypoints"]],
        }
        if with_select_button:
            data["buttons"] = SelectButton(id=row["id"])
        return cls(**data)

    sep = " · "


class SelectButton(Component):
    """<button hx-post="/tickets/{id}/select">Select</button>"""


class TicketDetail(Component):
    """
    <div class="ticket-view split-view">
    <article class="main">
    <header>
        <button hx-get="/tickets/{id}/edit" hx-target="#popoverholder">Edit</button>
        <h3>{id} <strong>{title}</strong></h3>
    </header>
    {summary}
    <footer>{comments}</footer>
    </article>
    <div class="sidebar">
    {properties}
    </div>
    </div>
    """


class TicketProperty(Component):
    """
    <p><strong>{key}:</strong> {value}</p>
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
                <li><button hx-get="/tickets/new" hx-target="#popoverholder">New ticket</button></li>
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


class TicketForm(Component):
    """
    <form hx-post="{endpoint}">
    <fieldset>
    <label>
        Summary
        <input
            name="summary"
            placeholder="Ticket summary"
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
    </fieldset>
    <input
        type="submit"
        value="Submit"
    >
    </form>
    """
