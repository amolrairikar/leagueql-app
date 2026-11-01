"""Yahoo OAuth endpoints: authorize redirect and callback."""

import json
import secrets
from typing import Annotated, Literal
from urllib.parse import urlencode, urlparse

import main
import yahoo_oauth
from dependencies import get_authenticated_user
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from main import (
    APIResponse,
    logger,
)

router = APIRouter()


@router.get("/leagues/yahoo/oauth/authorize", status_code=status.HTTP_200_OK)
def yahoo_authorize(
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
    leagueId: Annotated[
        str,
        Query(
            description="The Yahoo league id to resume onboarding for", max_length=100
        ),
    ],
    flow: Annotated[
        Literal["ONBOARD", "MIGRATE"],
        Query(
            description="Return context: ONBOARD returns to the landing page, MIGRATE to /migrate_league"
        ),
    ] = "ONBOARD",
    display: Annotated[
        Literal["page", "popup"],
        Query(
            description="How the callback hands the result back: page (302 redirect) or popup (postMessage + close)"
        ),
    ] = "page",
) -> APIResponse:
    """Start the Yahoo OAuth link (backend/yahoo-oauth).

    Mints a single-use ``state`` bound to the caller (carrying the pending ``leagueId``, the
    return-context ``flow``, and the ``display`` mode), persists it with a short TTL, and returns
    the Yahoo consent URL. The frontend opens that URL — in a popup for ``display=popup``, else a
    full-page redirect; the client secret never leaves the backend. The callback returns to the
    page selected by ``flow`` in the way selected by ``display``.
    """
    state, code_challenge = yahoo_oauth.create_oauth_state(
        clerk_user_id, leagueId, flow=flow, display=display
    )
    authorize_url = yahoo_oauth.build_authorize_url(state, code_challenge)
    return APIResponse(
        detail="Yahoo authorization URL generated",
        data={"authorize_url": authorize_url},
    )


@router.get("/leagues/yahoo/oauth/callback")
def yahoo_callback(
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> Response:
    """Handle Yahoo's OAuth redirect (backend/yahoo-oauth).

    Public route — Yahoo redirects the browser here with no Clerk JWT. Validates and
    single-use-consumes ``state``, exchanges the ``code`` for tokens, persists an encrypted
    ``YAHOO_OAUTH`` item, and hands the linked/declined result back to the frontend in the way
    the state's ``display`` selects: ``page`` → a ``302`` to the page chosen by the return-context
    ``flow`` (``MIGRATE`` -> ``/migrate_league``, else the landing page ``/``, which resumes
    onboarding inline); ``popup`` → a small HTML page that ``postMessage``s the opener and closes.
    ``state`` is consumed first — even on a declined link (Yahoo echoes it on
    ``error=access_denied``) — so the ``flow``/``display`` are recoverable; when no usable
    ``state`` is present the callback falls back to a ``page`` redirect to the landing page. A
    declined/invalid/failed link writes no token item and never reflects an external redirect
    target.
    """

    def _base_for_flow(flow: str) -> str:
        return (
            main.YAHOO_MIGRATE_RETURN_URL
            if flow == "MIGRATE"
            else main.YAHOO_CONNECT_RETURN_URL
        )

    def _return_url(linked: bool, return_base: str, league_id: str = "") -> str:
        params: dict[str, str] = {
            "platform": "YAHOO",
            "yahooLinked": "1" if linked else "0",
        }
        if linked and league_id:
            params["leagueId"] = league_id
        return f"{return_base}?{urlencode(params)}"

    def _popup_return(
        linked: bool, return_base: str, league_id: str = ""
    ) -> HTMLResponse:
        """Return an HTML page that hands the result to the opener via ``postMessage``.

        The consent ran in a popup, so we can't 302 the opener. This page posts the
        linked/declined result to the opener at the frontend's exact origin and closes; if it
        has no opener (the popup was blocked and consent opened in the same tab), it self-redirects
        to the page-mode return URL so onboarding still resumes inline. A per-response nonce CSP
        lets only this one inline script run — the API's default ``default-src 'none'`` CSP would
        otherwise block it.
        """
        message = {
            "source": "yahoo-oauth",
            "platform": "YAHOO",
            "yahooLinked": "1" if linked else "0",
        }
        if linked and league_id:
            message["leagueId"] = league_id
        target_origin = urlparse(return_base)
        target_origin = f"{target_origin.scheme}://{target_origin.netloc}"
        redirect_url = _return_url(linked, return_base, league_id)
        nonce = secrets.token_urlsafe(16)

        def _js(value: object) -> str:
            # Embed as a JS literal; escape ``<`` so a value can't break out of </script>.
            return json.dumps(value).replace("<", "\\u003c")

        # Server-controlled (driven by ``linked``, not user input), so safe to embed directly.
        heading = (
            "Yahoo sign-in complete! You can close this window."
            if linked
            else "Yahoo sign-in was not completed. You can close this window."
        )
        # The IIFE opens one brace with ``(function(){`` (``{{`` is an escaped literal ``{``),
        # so it must close with a single ``}`` before ``)();`` — an extra ``}`` is a JS syntax
        # error that stops the whole script (no postMessage, no auto-close).
        html = (
            '<!doctype html><html><head><meta charset="utf-8">'
            "<title>Yahoo sign-in</title></head><body>"
            f"<p>{heading}</p>"
            f'<script nonce="{nonce}">(function(){{'
            f"var msg={_js(message)};"
            "try{if(window.opener&&!window.opener.closed){"
            f"window.opener.postMessage(msg,{_js(target_origin)});"
            "window.close();return;}}catch(e){}"
            f"window.location.replace({_js(redirect_url)});"
            "})();</script></body></html>"
        )
        return HTMLResponse(
            content=html,
            headers={
                "Content-Security-Policy": (
                    f"default-src 'none'; script-src 'nonce-{nonce}'; "
                    "base-uri 'none'; frame-ancestors 'none'"
                ),
            },
        )

    def _result(
        linked: bool, return_base: str, display: str, league_id: str = ""
    ) -> Response:
        if display == "popup":
            return _popup_return(linked, return_base, league_id)
        return RedirectResponse(
            url=_return_url(linked, return_base, league_id),
            status_code=status.HTTP_302_FOUND,
        )

    # Consume state first (when present) so a single-use state is enforced and the return-context
    # ``flow``/``display`` are recoverable even when the user declined — otherwise a MIGRATE
    # decline would bounce the user to the landing page.
    state_payload = yahoo_oauth.consume_oauth_state(state) if state else None
    return_base = (
        _base_for_flow(state_payload.get("flow", "ONBOARD"))
        if state_payload
        else main.YAHOO_CONNECT_RETURN_URL
    )
    # No recoverable state → no known display; fall back to a page redirect (there is no opener
    # to postMessage in that case anyway).
    display = state_payload.get("display", "page") if state_payload else "page"

    if error or not code or state_payload is None:
        logger.info(
            "Yahoo callback declined or missing/invalid state (error=%s)", error
        )
        return _result(linked=False, return_base=return_base, display=display)

    try:
        token_response = yahoo_oauth.exchange_code_for_tokens(
            code, state_payload["code_verifier"]
        )
        yahoo_oauth.store_tokens(state_payload["clerk_user_id"], token_response)
    except Exception as e:  # noqa: BLE001  any exchange/storage failure → declined marker
        logger.error("Yahoo code exchange failed: %s", type(e).__name__)
        return _result(linked=False, return_base=return_base, display=display)

    logger.info("Yahoo account linked for user")
    return _result(
        linked=True,
        return_base=return_base,
        display=display,
        league_id=state_payload["league_id"],
    )
