"""Shared Yahoo Fantasy members fetch/parse (backend/yahoo-members-proxy).

The migration flow maps each source-platform manager to a destination member. For a Yahoo
destination that member list is a Yahoo league's managers, fetched server-side with the
caller's linked OAuth access token (the token never reaches the browser). This module holds
that fetch/parse so the API Lambda can use it without importing the onboarder's full Yahoo
client (which pulls ``aiohttp`` and the onboarding machinery).

The pure JSON-normalization helpers (``_flatten``, ``_collection_items``, ``_league_subresource``)
live here as the single source of truth; ``onboarder.yahoo_client`` imports them from here.
Yahoo's ``?format=json`` uses deeply nested, numeric-keyed containers, so these normalize them
into plain dicts/lists.
"""

from typing import Any

YAHOO_BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"


class YahooLeagueNotFound(Exception):
    """A numeric Yahoo league id is not among the linked user's NFL leagues.

    Yahoo only exposes leagues the authenticated user belongs to, so this maps to a ``404``
    ("that league isn't in your Yahoo account") distinct from an upstream ``502``.
    """


# --------------------------------------------------------------------------------------
# Yahoo JSON normalization helpers (single source of truth; also used by onboarder.yahoo_client)
# --------------------------------------------------------------------------------------
def _flatten(node: Any) -> dict[str, Any]:
    """Merge Yahoo's list-of-single-key-dicts entity representation into one flat dict.

    Yahoo represents an entity (team, player, transaction, ...) as a list whose elements are
    either single-key dicts (base attributes) or nested lists of the same. Non-dict / empty
    elements are ignored. A plain dict is returned as-is.
    """
    if isinstance(node, dict):
        return node
    merged: dict[str, Any] = {}
    if isinstance(node, list):
        for element in node:
            if isinstance(element, dict):
                merged.update(element)
            elif isinstance(element, list):
                merged.update(_flatten(element))
    return merged


def _collection_items(container: Any, inner_key: str) -> list[Any]:
    """Return the inner objects of a Yahoo collection.

    Yahoo returns a collection in one of two shapes: a numeric-keyed object
    ``{"0": {inner_key: X0}, "1": {inner_key: X1}, ..., "count": N}`` (used for large
    collections like a league's teams or a roster's players) or a plain list
    ``[{inner_key: X0}, {inner_key: X1}, ...]`` (used for small nested sub-collections
    like a team's ``managers`` or ``team_logos``). Handles both, returning ``[X0, X1, ...]``
    in index order and tolerating a missing/empty container.
    """
    if isinstance(container, list):
        return [
            element[inner_key]
            for element in container
            if isinstance(element, dict) and inner_key in element
        ]
    if not isinstance(container, dict):
        return []
    items = []
    index = 0
    while str(index) in container:
        entry = container[str(index)]
        index += 1
        if isinstance(entry, dict) and inner_key in entry:
            items.append(entry[inner_key])
    return items


def _league_subresource(payload: dict[str, Any], key: str) -> Any:
    """Return the ``key`` sub-resource object from a ``/league/{key}/{sub}`` JSON payload.

    ``fantasy_content.league`` is ``[meta, {sub: ...}, ...]``; scan the trailing elements for
    the one carrying ``key``.
    """
    league = payload.get("fantasy_content", {}).get("league", [])
    for element in league[1:] if isinstance(league, list) else []:
        if isinstance(element, dict) and key in element:
            return element[key]
    return None


# --------------------------------------------------------------------------------------
# Members fetch/parse
# --------------------------------------------------------------------------------------
def _index_user_leagues(payload: dict[str, Any]) -> dict[str, dict]:
    """Parse the user→games→leagues enumeration into an id-indexed league-meta map."""
    by_id: dict[str, dict] = {}
    users = _collection_items(
        payload.get("fantasy_content", {}).get("users", {}), "user"
    )
    for user in users:
        games = _collection_items(_flatten(user).get("games", {}), "game")
        for game in games:
            leagues = _collection_items(_flatten(game).get("leagues", {}), "league")
            for league in leagues:
                meta = _flatten(league[0] if isinstance(league, list) else league)
                if meta.get("league_id"):
                    by_id[str(meta["league_id"])] = meta
    return by_id


def resolve_league_key(
    user_leagues_payload: dict[str, Any], numeric_league_id: str
) -> str | None:
    """Resolve a numeric Yahoo league id to its ``league_key`` from the user's NFL leagues.

    Returns ``None`` when the entered id is not among the linked user's leagues (Yahoo only
    enumerates leagues the caller belongs to).
    """
    meta = _index_user_leagues(user_leagues_payload).get(str(numeric_league_id))
    return meta.get("league_key") if meta else None


def parse_managers(teams_payload: dict[str, Any]) -> list[dict[str, str]]:
    """Parse a ``/league/{key}/teams`` payload into ``[{owner_id, display_name}]``.

    ``owner_id`` is the primary manager's stable cross-season Yahoo ``guid`` (falling back to
    ``manager_id``); ``display_name`` is the manager ``nickname``, falling back to ``owner_id``.
    Teams whose primary manager has no id are skipped.
    """
    teams = _collection_items(_league_subresource(teams_payload, "teams") or {}, "team")
    managers: list[dict[str, str]] = []
    for team in teams:
        flat = _flatten(team)
        team_managers = _collection_items(flat.get("managers", {}), "manager")
        primary = _flatten(team_managers[0]) if team_managers else {}
        owner_id = primary.get("guid") or primary.get("manager_id")
        if not owner_id:
            continue
        managers.append(
            {"owner_id": owner_id, "display_name": primary.get("nickname") or owner_id}
        )
    return managers


def fetch_yahoo_members(
    access_token: str, numeric_league_id: str, *, http: Any
) -> list[dict[str, str]]:
    """Fetch a Yahoo league's managers using the caller's access token.

    Enumerates the caller's NFL leagues to resolve ``numeric_league_id`` → ``league_key``
    (raising ``YahooLeagueNotFound`` when the league isn't the caller's), then fetches that
    league's teams and returns ``[{owner_id, display_name}]``.

    Args:
        access_token: A valid Yahoo access token for the caller.
        numeric_league_id: The entered destination Yahoo (numeric) league id.
        http: A ``requests``-like module used for the two authenticated GETs (injected so the
            caller controls timeouts/patching).

    Raises:
        YahooLeagueNotFound: the id is not among the caller's Yahoo leagues.
        requests.HTTPError / RequestException / ValueError: on a Yahoo HTTP, network, or parse
            failure (surfaced by the caller as ``502``).
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    leagues_url = (
        f"{YAHOO_BASE_URL}/users;use_login=1/games;game_codes=nfl/leagues?format=json"
    )
    leagues_response = http.get(leagues_url, headers=headers, timeout=10)
    leagues_response.raise_for_status()
    league_key = resolve_league_key(leagues_response.json(), numeric_league_id)
    if league_key is None:
        raise YahooLeagueNotFound(numeric_league_id)

    teams_url = f"{YAHOO_BASE_URL}/league/{league_key}/teams?format=json"
    teams_response = http.get(teams_url, headers=headers, timeout=10)
    teams_response.raise_for_status()
    return parse_managers(teams_response.json())
