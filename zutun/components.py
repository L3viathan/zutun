from collections import defaultdict


STATES = ["ToDo", "Ongoing", "Blocked", "Done"]


class Component:
    sep = ""
    def __init__(self, *args, **kwargs):
        self.kwargs = defaultdict(
            str,
            {
                **{f"_{i}": arg or "" for i, arg in enumerate(args)},
                 **{k: v or "" for k, v in kwargs.items()}
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
    <article class="ticket-card" hx-drag='{{"ticket": "{id}"}}' draggable="{draggable}">
      {buttons}
      <a href="/tickets/{id}"><span class="id">{id}</span> <strong>{summary}</strong></a><br>
      <small>{details}</small>
    </article>
    """

    @classmethod
    def from_row(cls, row, with_select_button=False, draggable=False):
        data = {
            "id": row["id"],
            "summary": row["summary"],
            "details": [row["assignee"], Storypoints(row["storypoints"])],
        }
        if with_select_button:
            data["buttons"] = SelectButton(id=row["id"])
        data["draggable"] = str(draggable).lower()
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
        <h3><span class="id">{id}</span> <strong>{title}</strong></h3>
    </header>
    {summary}
    <footer>
    {comments}
    <form hx-post="/tickets/{id}/comments">
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


class TicketProperty(Component):
    """
    <p><strong>{_0}:</strong> {_1}</p>
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
    </fieldset>
    <input
        type="submit"
        value="Submit"
    >
    </form>
    """


class Storypoints(Component):
    """<span class="storypoints">{_0}</span>"""


class StateSelector(Component):
    """
    <form>
    <input type="hidden" name="ticket" value="{ticket_id}">
    <select name="state" hx-put="/tickets/state">
        {options}
    </select>
    </form>
    """

    @classmethod
    def from_ticket(cls, ticket):
        return cls(
            ticket_id=ticket["id"],
            options=[
                StateOption(
                    state=state,
                    selected="selected" if state == ticket["state"] else "",
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
