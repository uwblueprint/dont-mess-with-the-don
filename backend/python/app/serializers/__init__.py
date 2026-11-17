"""Build API responses from table rows.

Each serializer turns stored object keys into the URLs a response returns, using the
storage service's `url_for`. Keeping this here means ORM models never know about
storage, and routes don't repeat the conversion.
"""
