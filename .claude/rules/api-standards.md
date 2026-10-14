# API Standards

## Typed clients — always use them for new modules

Every HTTP call for a new feature module MUST go through a typed client extending
`BaseAPIClient` (`api/base_client.py`), never `api_session.get/post/put(...)` with a raw path
called directly from a test or conftest fixture.

```python
# CORRECT
def test_creates_resource(self, orders_api_client, ...):
    response = orders_api_client.create_order(payload)

# WRONG — raw path in test code
def test_creates_resource(self, api_session, ...):
    response = api_session.post(APIPath.ORDERS, json=payload)
```

`tests/e2e/users/` uses `api/users_client.py`'s `UsersClient` for exactly this reason — see it
for a real, worked example of the typed-client pattern.

## Endpoint paths live in `src/core/constants.py::APIPath`, not `.env`

This boilerplate resolves endpoints as compile-time Python constants (`APIPath.ORDERS`,
`APIPath.ORDER_BY_ID = "/orders/{id}"`, substituted via `str.format`), not via env vars — that's
the existing, established convention (see `tests/e2e/users/` and `APIPath` itself). Add new
endpoints there, never hardcode a path string inline in a client or a test.

## `BaseAPIClient` public interface

```python
client.get(path, **kwargs)                          # plain GET
client.post(path, json=None, **kwargs)               # plain POST
client.put(path, json=None, **kwargs)                # plain PUT
client.patch(path, json=None, **kwargs)              # plain PATCH
client.delete(path, **kwargs)                        # plain DELETE
client.get_path(path_template, path_params, **kwargs)   # GET + "{param}" substitution
client.get_with_path(path, *segments, **kwargs)         # GET + appended path segments
client.url_for(path_template, **path_params)         # resolve a full URL (for paginators)
client.base_url                                      # API base URL (property)
client.session                                       # underlying APISession (for pagination)
```

## Pattern — endpoint with a path parameter (`"{id}"`-style template)

```python
# In api/orders_client.py
def get_order(self, order_id: int | str, **kwargs) -> requests.Response:
    return self.get_path(APIPath.ORDER_BY_ID, {"id": order_id}, **kwargs)
```

## Pattern — endpoint with appended path segments (no fixed template)

```python
# In api/orders_client.py
def get_order_notes(self, order_id: int, note_type: str, **kwargs) -> requests.Response:
    return self.get_with_path(APIPath.ORDER_NOTES, order_id, note_type, **kwargs)
```

## Pattern — raw URL needed for a pagination helper

```python
def orders_url(self, **path_params) -> str:
    return self.url_for(APIPath.ORDERS, **path_params)
```

## Legitimate exceptions (do NOT force through a typed client)

1. **Pagination link-following** — `client.session.get(next_link)` where `next_link` is a full
   URL from a response body. Reuse `client.session` (the underlying `APISession`) so auth stays
   consistent — never build a second, separately-authenticated session.
2. **Downloads needing a different auth token** (e.g. S3/PDF links with a bearer token instead
   of the primary session's auth) — a plain `requests.get(url, headers=...)` call is fine here.
3. **A path genuinely not in `APIPath` yet** — add it to `src/core/constants.py` first; only
   fall back to a raw `client.session.get(url)` call if it truly can't be a named constant.
4. **Multi-endpoint iterator helpers** that loop over a dynamic list of path templates may
   build paths directly — callers must still go through the client, not raw `api_session`.

## Adding a new module's client

1. Create `api/<module>_client.py` extending `BaseAPIClient` — one method per endpoint, named
   after the business action, not the HTTP verb (`create_order`, not `post_order`).
2. Add a module-scoped `<module>_api_client(api_session)` fixture in that module's `conftest.py`.
3. Never use `api_session` directly in test files for endpoint calls — inject the typed client
   fixture instead.

See `.claude/skills/generate-api-client/SKILL.md` to scaffold a new client, and
`.claude/rules/assertions.md` for assertion/DB-sync standards.
