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
    <article hx-ext="drag" class="grid kanban">
      {columns}
    </article>
    """

class Backlog(Component):
    """
    <article>
      {items}
    </article>
    """


class KanbanColumn(Component):
    """
    <div class="kanban-col kanban-col-{name}">
      <h4>{name}</h4>
      <hr>
      <div class="kanban-col-items" hx-drop='{{"state": "{name}"}}' hx-drop-action="/ticket/{number}/state">
        {items}
      </div>
    </div>
    """


class TicketCard(Component):
    """
    <article class="ticket-card" hx-ext="drag" hx-drag='{{"ticket": "{number}"}}' hx-drag-action="/ticket/{number}/state" draggable="true">
      {number} <strong>{title}</strong><br>
      <small>{details}</small>
    </article>
    """

    sep = " · "


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
        <nav>
            <ul>
                <li>zutun</li>
                <li><a href="/">Board</a></li>
                <li><a href="/backlog">Backlog</a></li>
            </ul>
            <ul>
                <li>Search</li>
            </ul>
        </nav>
        <main>
            {body}
        </main>
    </body>
    </html>
    """
