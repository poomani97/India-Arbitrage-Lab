def goto(at, page):
    """Open a page of the sidebar menu in an AppTest and return the app."""
    at.sidebar.radio(key="menu").set_value(page).run(timeout=90)
    return at
