from django.views.generic import TemplateView


class PageView(TemplateView):
    """Serves a static HTML shell; all data is loaded from the JSON API by vanilla JS.

    The token lives in localStorage rather than a session, so per-page
    ``login_required`` guards would be a false signal. The API is the
    authorization boundary and the frontend redirects unauthenticated visitors.
    """
