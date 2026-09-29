import json
import secrets
import sys
import time

from datetime import (
    date,
    timedelta
)

from getpass import getpass

from urllib.error import (
    HTTPError,
    URLError
)

from urllib.parse import (
    urlencode
)

from urllib.request import (
    Request,
    urlopen
)


# =========================================================
# CONFIG
# =========================================================

BASE_URL = "http://127.0.0.1:8000"

DEFAULT_TIMEOUT = 30
AI_TIMEOUT = 180

TEST_SYMBOL = "FPT"
INVALID_SYMBOL = "ZZZZZZ"
TOO_LONG_SYMBOL = "ABCDEFGHIJK"


# =========================================================
# RESULT STORAGE
# =========================================================

results = []

temp_username = None
temp_password = None
temp_user_id = None

user_token = None
admin_token = None

conversation_id = None

watchlist_exists = False
conversation_exists = False
temp_user_exists = False


# =========================================================
# EXCEPTIONS
# =========================================================

class RegressionError(Exception):
    pass


# =========================================================
# HTTP HELPERS
# =========================================================

def api_request(
    method,
    path,
    *,
    token=None,
    json_body=None,
    form_body=None,
    query=None,
    timeout=DEFAULT_TIMEOUT
):

    url = (
        BASE_URL
        + path
    )


    if query:

        encoded_query = urlencode(
            query
        )

        url = (
            f"{url}?{encoded_query}"
        )


    headers = {
        "Accept": "application/json"
    }


    if token:

        headers[
            "Authorization"
        ] = (
            f"Bearer {token}"
        )


    body = None


    if json_body is not None:

        body = json.dumps(
            json_body
        ).encode(
            "utf-8"
        )

        headers[
            "Content-Type"
        ] = (
            "application/json"
        )


    elif form_body is not None:

        body = urlencode(
            form_body
        ).encode(
            "utf-8"
        )

        headers[
            "Content-Type"
        ] = (
            "application/x-www-form-urlencoded"
        )


    request = Request(
        url=url,
        data=body,
        headers=headers,
        method=method.upper()
    )


    try:

        with urlopen(
            request,
            timeout=timeout
        ) as response:

            raw = response.read().decode(
                "utf-8"
            )

            status = response.status


    except HTTPError as exc:

        status = exc.code

        raw = exc.read().decode(
            "utf-8",
            errors="replace"
        )


    except URLError as exc:

        raise RegressionError(
            f"Could not connect to backend: {exc}"
        ) from exc


    except TimeoutError as exc:

        raise RegressionError(
            f"Request timed out: {method} {path}"
        ) from exc


    if not raw:

        return status, None


    try:

        return (
            status,
            json.loads(
                raw
            )
        )


    except json.JSONDecodeError:

        return (
            status,
            raw
        )


# =========================================================
# ASSERT HELPERS
# =========================================================

def body_preview(
    body,
    limit=500
):

    try:

        text = json.dumps(
            body,
            ensure_ascii=False
        )

    except Exception:

        text = str(
            body
        )


    if len(text) > limit:

        return (
            text[:limit]
            + "..."
        )


    return text


def expect_status(
    status,
    allowed,
    body=None
):

    if isinstance(
        allowed,
        int
    ):

        allowed = {
            allowed
        }

    else:

        allowed = set(
            allowed
        )


    if status not in allowed:

        raise RegressionError(
            f"Expected HTTP {sorted(allowed)}, "
            f"got {status}. "
            f"Body: {body_preview(body)}"
        )


def expect(
    condition,
    message
):

    if not condition:

        raise RegressionError(
            message
        )


# =========================================================
# TEST RUNNER
# =========================================================

def run_test(
    name,
    func,
    *,
    critical=False
):

    start = time.perf_counter()


    try:

        value = func()

        duration = (
            time.perf_counter()
            - start
        )

        results.append(
            (
                name,
                True,
                duration,
                None
            )
        )

        print(
            f"[PASS] {name} "
            f"({duration:.2f}s)"
        )

        return value


    except Exception as exc:

        duration = (
            time.perf_counter()
            - start
        )

        results.append(
            (
                name,
                False,
                duration,
                str(exc)
            )
        )

        print(
            f"[FAIL] {name} "
            f"({duration:.2f}s)"
        )

        print(
            f"       {exc}"
        )


        if critical:

            raise


        return None


# =========================================================
# DATA HELPERS
# =========================================================

def extract_list(
    body
):

    if isinstance(
        body,
        list
    ):

        return body


    if isinstance(
        body,
        dict
    ):

        for key in (
            "data",
            "items",
            "users",
            "conversations",
            "watchlist",
            "history",
            "messages"
        ):

            value = body.get(
                key
            )

            if isinstance(
                value,
                list
            ):

                return value


    return []


def login(
    username,
    password
):

    status, body = api_request(
        "POST",
        "/login",
        form_body={
            "username": username,
            "password": password
        }
    )

    expect_status(
        status,
        200,
        body
    )

    expect(
        isinstance(
            body,
            dict
        ),
        "Login response is not an object"
    )

    token = body.get(
        "access_token"
    )

    expect(
        bool(token),
        "Login response has no access_token"
    )

    return token


# =========================================================
# CLEANUP
# =========================================================

def emergency_cleanup():

    global watchlist_exists
    global conversation_exists
    global temp_user_exists


    print()
    print(
        "===== EMERGENCY CLEANUP ====="
    )


    if (
        watchlist_exists
        and user_token
    ):

        try:

            api_request(
                "DELETE",
                f"/watchlist/{TEST_SYMBOL}",
                token=user_token
            )

            print(
                "[CLEANUP] Watchlist attempted"
            )

            watchlist_exists = False

        except Exception as exc:

            print(
                "[CLEANUP WARNING] Watchlist:",
                exc
            )


    if (
        conversation_exists
        and conversation_id
        and user_token
    ):

        try:

            api_request(
                "DELETE",
                (
                    f"/conversations/"
                    f"{conversation_id}"
                ),
                token=user_token
            )

            print(
                "[CLEANUP] Conversation attempted"
            )

            conversation_exists = False

        except Exception as exc:

            print(
                "[CLEANUP WARNING] Conversation:",
                exc
            )


    if (
        temp_user_exists
        and temp_user_id
        and admin_token
    ):

        try:

            api_request(
                "DELETE",
                (
                    f"/admin/users/"
                    f"{temp_user_id}"
                ),
                token=admin_token
            )

            print(
                "[CLEANUP] Temporary user attempted"
            )

            temp_user_exists = False

        except Exception as exc:

            print(
                "[CLEANUP WARNING] User:",
                exc
            )


# =========================================================
# MAIN REGRESSION
# =========================================================

def main():

    global temp_username
    global temp_password
    global temp_user_id

    global user_token
    global admin_token

    global conversation_id

    global watchlist_exists
    global conversation_exists
    global temp_user_exists


    print()
    print(
        "=" * 68
    )

    print(
        "FINAL BACKEND REGRESSION TEST"
    )

    print(
        "=" * 68
    )

    print(
        f"Backend: {BASE_URL}"
    )

    print()


    # -----------------------------------------------------
    # BASIC SERVER
    # -----------------------------------------------------

    def test_health():

        status, body = api_request(
            "GET",
            "/health"
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            isinstance(
                body,
                dict
            ),
            "Health response is not JSON object"
        )

        expect(
            body.get("status")
            == "ok",
            (
                "Health status is not ok: "
                f"{body}"
            )
        )

        expect(
            body.get("database")
            == "connected",
            (
                "Database is not connected: "
                f"{body}"
            )
        )


    run_test(
        "Health endpoint",
        test_health,
        critical=True
    )


    def test_root():

        status, body = api_request(
            "GET",
            "/"
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            isinstance(
                body,
                dict
            )
            and bool(
                body.get(
                    "message"
                )
            ),
            "Root response has no message"
        )


    run_test(
        "Root endpoint",
        test_root
    )


    # -----------------------------------------------------
    # AUTH WITHOUT TOKEN
    # -----------------------------------------------------

    def test_unauthorized_me():

        status, body = api_request(
            "GET",
            "/me"
        )

        expect_status(
            status,
            401,
            body
        )


    run_test(
        "Unauthorized /me -> 401",
        test_unauthorized_me
    )


    def test_unauthorized_stock():

        status, body = api_request(
            "POST",
            (
                f"/stocks/"
                f"{TEST_SYMBOL}"
                "/analyze/structured"
            )
        )

        expect_status(
            status,
            401,
            body
        )


    run_test(
        "Unauthorized structured stock -> 401",
        test_unauthorized_stock
    )


    # -----------------------------------------------------
    # ADMIN LOGIN FIRST
    # Ensures cleanup is available before creating test user.
    # -----------------------------------------------------

    print()
    print(
        "Existing admin credentials are required."
    )

    print(
        "The password is entered locally and is not printed."
    )

    admin_username = input(
        "Admin username: "
    ).strip()

    admin_password = getpass(
        "Admin password: "
    )


    expect(
        bool(
            admin_username
        ),
        "Admin username cannot be empty"
    )


    def test_admin_login():

        return login(
            admin_username,
            admin_password
        )


    admin_token = run_test(
        "Admin login",
        test_admin_login,
        critical=True
    )


    def test_admin_users_initial():

        status, body = api_request(
            "GET",
            "/admin/users",
            token=admin_token
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            isinstance(
                extract_list(
                    body
                ),
                list
            ),
            "Admin users response is invalid"
        )


    run_test(
        "Admin list users",
        test_admin_users_initial,
        critical=True
    )


    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    def test_register_validation():

        status, body = api_request(
            "POST",
            "/register",
            json_body={
                "username": "ab",
                "password": "123"
            }
        )

        expect_status(
            status,
            422,
            body
        )


    run_test(
        "Register validation -> 422",
        test_register_validation
    )


    # -----------------------------------------------------
    # REGISTER TEMP USER
    # -----------------------------------------------------

    timestamp = time.strftime(
        "%Y%m%d%H%M%S"
    )

    suffix = secrets.token_hex(
        2
    )

    temp_username = (
        f"regtest_{timestamp}_{suffix}"
    )

    temp_password = (
        "RegTest_"
        + secrets.token_urlsafe(
            12
        )
    )


    print()
    print(
        f"Temporary username: {temp_username}"
    )


    def test_register():

        nonlocal_dummy = None

        status, body = api_request(
            "POST",
            "/register",
            json_body={
                "username": temp_username,
                "password": temp_password
            }
        )

        expect_status(
            status,
            {
                200,
                201
            },
            body
        )

        expect(
            isinstance(
                body,
                dict
            ),
            "Register response is not an object"
        )

        expect(
            body.get(
                "username"
            )
            == temp_username,
            (
                "Registered username mismatch: "
                f"{body}"
            )
        )

        expect(
            body.get(
                "role"
            )
            == "user",
            (
                "New account should have user role: "
                f"{body}"
            )
        )

        user_id = body.get(
            "id"
        )

        expect(
            isinstance(
                user_id,
                int
            ),
            (
                "Register response does not contain "
                "integer user id"
            )
        )

        return user_id


    temp_user_id = run_test(
        "Register temporary user",
        test_register,
        critical=True
    )

    temp_user_exists = True


    # -----------------------------------------------------
    # DUPLICATE REGISTER
    # -----------------------------------------------------

    def test_duplicate_register():

        status, body = api_request(
            "POST",
            "/register",
            json_body={
                "username": temp_username,
                "password": temp_password
            }
        )

        expect_status(
            status,
            {
                400,
                409
            },
            body
        )


    run_test(
        "Duplicate register rejected",
        test_duplicate_register
    )


    # -----------------------------------------------------
    # WRONG PASSWORD
    # -----------------------------------------------------

    def test_wrong_password():

        status, body = api_request(
            "POST",
            "/login",
            form_body={
                "username": temp_username,
                "password": (
                    temp_password
                    + "_wrong"
                )
            }
        )

        expect_status(
            status,
            401,
            body
        )


    run_test(
        "Wrong password -> 401",
        test_wrong_password
    )


    # -----------------------------------------------------
    # USER LOGIN
    # -----------------------------------------------------

    def test_user_login():

        return login(
            temp_username,
            temp_password
        )


    user_token = run_test(
        "User login",
        test_user_login,
        critical=True
    )


    # -----------------------------------------------------
    # /ME
    # -----------------------------------------------------

    def test_me():

        status, body = api_request(
            "GET",
            "/me",
            token=user_token
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "username"
            )
            == temp_username,
            (
                "/me username mismatch: "
                f"{body}"
            )
        )

        expect(
            body.get(
                "role"
            )
            == "user",
            (
                "/me expected user role: "
                f"{body}"
            )
        )


    run_test(
        "Authenticated /me",
        test_me
    )


    # -----------------------------------------------------
    # REGULAR USER MUST NOT ACCESS ADMIN
    # -----------------------------------------------------

    def test_user_admin_forbidden():

        status, body = api_request(
            "GET",
            "/admin/users",
            token=user_token
        )

        expect_status(
            status,
            403,
            body
        )


    run_test(
        "Regular user denied admin access",
        test_user_admin_forbidden
    )


    # -----------------------------------------------------
    # WATCHLIST
    # -----------------------------------------------------

    def test_watchlist_add():

        status, body = api_request(
            "POST",
            "/watchlist",
            token=user_token,
            json_body={
                "symbol": TEST_SYMBOL
            }
        )

        expect_status(
            status,
            {
                200,
                201
            },
            body
        )

        expect(
            isinstance(
                body,
                dict
            ),
            "Watchlist add response invalid"
        )

        expect(
            body.get(
                "symbol"
            )
            == TEST_SYMBOL,
            (
                "Watchlist symbol mismatch: "
                f"{body}"
            )
        )


    run_test(
        "Watchlist add FPT",
        test_watchlist_add,
        critical=True
    )

    watchlist_exists = True


    def test_watchlist_get():

        status, body = api_request(
            "GET",
            "/watchlist",
            token=user_token
        )

        expect_status(
            status,
            200,
            body
        )

        items = extract_list(
            body
        )

        symbols = [
            str(
                item.get(
                    "symbol",
                    ""
                )
            ).upper()
            for item in items
            if isinstance(
                item,
                dict
            )
        ]

        expect(
            TEST_SYMBOL
            in symbols,
            (
                f"{TEST_SYMBOL} not found "
                f"in watchlist: {body}"
            )
        )


    run_test(
        "Watchlist get",
        test_watchlist_get
    )


    def test_watchlist_duplicate():

        status, body = api_request(
            "POST",
            "/watchlist",
            token=user_token,
            json_body={
                "symbol": TEST_SYMBOL
            }
        )

        expect_status(
            status,
            {
                400,
                409
            },
            body
        )


    run_test(
        "Duplicate watchlist rejected",
        test_watchlist_duplicate
    )


    # -----------------------------------------------------
    # CONVERSATIONS
    # -----------------------------------------------------

    def test_conversation_create():

        status, body = api_request(
            "POST",
            "/conversations",
            token=user_token,
            json_body={
                "title": (
                    "Final Regression Test"
                )
            }
        )

        expect_status(
            status,
            {
                200,
                201
            },
            body
        )

        expect(
            isinstance(
                body,
                dict
            ),
            "Conversation create response invalid"
        )

        value = body.get(
            "id"
        )

        expect(
            isinstance(
                value,
                int
            ),
            "Conversation id missing"
        )

        return value


    conversation_id = run_test(
        "Conversation create",
        test_conversation_create,
        critical=True
    )

    conversation_exists = True


    def test_conversation_get():

        status, body = api_request(
            "GET",
            (
                f"/conversations/"
                f"{conversation_id}"
            ),
            token=user_token
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "id"
            )
            == conversation_id,
            (
                "Conversation id mismatch: "
                f"{body}"
            )
        )


    run_test(
        "Conversation get",
        test_conversation_get
    )


    def test_conversation_list():

        status, body = api_request(
            "GET",
            "/conversations",
            token=user_token
        )

        expect_status(
            status,
            200,
            body
        )

        items = extract_list(
            body
        )

        ids = [
            item.get(
                "id"
            )
            for item in items
            if isinstance(
                item,
                dict
            )
        ]

        expect(
            conversation_id
            in ids,
            (
                "Conversation missing "
                "from conversation list"
            )
        )


    run_test(
        "Conversation list",
        test_conversation_list
    )


    def test_conversation_update():

        status, body = api_request(
            "PATCH",
            (
                f"/conversations/"
                f"{conversation_id}"
            ),
            token=user_token,
            json_body={
                "title": (
                    "Regression Updated"
                )
            }
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "title"
            )
            == "Regression Updated",
            (
                "Conversation title was "
                f"not updated: {body}"
            )
        )


    run_test(
        "Conversation update",
        test_conversation_update
    )


    # -----------------------------------------------------
    # GENERAL CHAT
    # -----------------------------------------------------

    def test_general_chat():

        status, body = api_request(
            "POST",
            (
                f"/conversations/"
                f"{conversation_id}/chat"
            ),
            token=user_token,
            json_body={
                "message": (
                    "Chào bạn. Hãy trả lời "
                    "ngắn gọn rằng hệ thống "
                    "đang hoạt động."
                )
            },
            timeout=AI_TIMEOUT
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            isinstance(
                body,
                dict
            ),
            "Chat response invalid"
        )

        expect(
            bool(
                body.get(
                    "answer"
                )
            ),
            (
                "General chat returned "
                "empty answer"
            )
        )


    run_test(
        "General AI chat",
        test_general_chat
    )


    # -----------------------------------------------------
    # STOCK-AWARE CHAT
    # -----------------------------------------------------

    def test_stock_chat():

        status, body = api_request(
            "POST",
            (
                f"/conversations/"
                f"{conversation_id}/chat"
            ),
            token=user_token,
            json_body={
                "message": (
                    "Hãy mô tả ngắn gọn dữ liệu "
                    "hiện có của FPT, không đưa "
                    "khuyến nghị mua bán."
                ),
                "symbol": TEST_SYMBOL
            },
            timeout=AI_TIMEOUT
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            bool(
                body.get(
                    "answer"
                )
            ),
            (
                "Stock-aware chat returned "
                "empty answer"
            )
        )


    run_test(
        "Stock-aware conversation chat",
        test_stock_chat
    )


    # -----------------------------------------------------
    # CHAT HISTORY
    # -----------------------------------------------------

    def test_chat_history():

        status, body = api_request(
            "GET",
            (
                f"/conversations/"
                f"{conversation_id}/history"
            ),
            token=user_token
        )

        expect_status(
            status,
            200,
            body
        )

        items = extract_list(
            body
        )

        expect(
            len(
                items
            )
            >= 2,
            (
                "Expected at least 2 chat "
                f"history items, got {len(items)}"
            )
        )


    run_test(
        "Conversation history",
        test_chat_history
    )


    # -----------------------------------------------------
    # STOCK HISTORY
    # -----------------------------------------------------

    def test_stock_history():

        end_date = date.today()

        start_date = (
            end_date
            - timedelta(
                days=45
            )
        )

        status, body = api_request(
            "GET",
            (
                f"/stocks/"
                f"{TEST_SYMBOL}/history"
            ),
            token=user_token,
            query={
                "start": (
                    start_date
                    .isoformat()
                ),
                "end": (
                    end_date
                    .isoformat()
                ),
                "interval": "1D"
            },
            timeout=AI_TIMEOUT
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "symbol"
            )
            == TEST_SYMBOL,
            (
                "Stock history symbol "
                f"mismatch: {body}"
            )
        )

        expect(
            body.get(
                "count",
                0
            )
            > 0,
            "Stock history is empty"
        )


    run_test(
        "Stock history",
        test_stock_history
    )


    # -----------------------------------------------------
    # STOCK LATEST
    # -----------------------------------------------------

    def test_stock_latest():

        status, body = api_request(
            "GET",
            (
                f"/stocks/"
                f"{TEST_SYMBOL}/latest"
            ),
            token=user_token,
            timeout=AI_TIMEOUT
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "symbol"
            )
            == TEST_SYMBOL,
            (
                "Latest stock symbol "
                f"mismatch: {body}"
            )
        )


    run_test(
        "Stock latest",
        test_stock_latest
    )


    # -----------------------------------------------------
    # COMPANY
    # -----------------------------------------------------

    def test_company():

        status, body = api_request(
            "GET",
            (
                f"/stocks/"
                f"{TEST_SYMBOL}/company"
            ),
            token=user_token,
            timeout=AI_TIMEOUT
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "symbol"
            )
            == TEST_SYMBOL,
            "Company symbol mismatch"
        )


    run_test(
        "Company info",
        test_company
    )


    # -----------------------------------------------------
    # FUNDAMENTALS
    # -----------------------------------------------------

    def test_fundamentals():

        status, body = api_request(
            "GET",
            (
                f"/stocks/"
                f"{TEST_SYMBOL}/fundamentals"
            ),
            token=user_token,
            query={
                "period": "quarter"
            },
            timeout=AI_TIMEOUT
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "count",
                0
            )
            > 0,
            "Fundamentals are empty"
        )


    run_test(
        "Fundamentals",
        test_fundamentals
    )


    # -----------------------------------------------------
    # NEWS
    # -----------------------------------------------------

    def test_news():

        status, body = api_request(
            "GET",
            (
                f"/stocks/"
                f"{TEST_SYMBOL}/news"
            ),
            token=user_token,
            query={
                "limit": 8
            },
            timeout=AI_TIMEOUT
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "symbol"
            )
            == TEST_SYMBOL,
            "News symbol mismatch"
        )

        expect(
            isinstance(
                body.get(
                    "data",
                    []
                ),
                list
            ),
            "News data is not a list"
        )


    run_test(
        "Stock news",
        test_news
    )


    # -----------------------------------------------------
    # NORMAL STOCK ANALYSIS
    # -----------------------------------------------------

    def test_normal_analysis():

        status, body = api_request(
            "POST",
            (
                f"/stocks/"
                f"{TEST_SYMBOL}/analyze"
            ),
            token=user_token,
            json_body={
                "question": (
                    "Tóm tắt dữ liệu hiện có "
                    "của FPT một cách trung tính."
                )
            },
            timeout=AI_TIMEOUT
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "symbol"
            )
            == TEST_SYMBOL,
            "Normal analysis symbol mismatch"
        )

        expect(
            bool(
                body.get(
                    "answer"
                )
            ),
            "Normal analysis answer is empty"
        )


    run_test(
        "Normal stock AI analysis",
        test_normal_analysis
    )


    # -----------------------------------------------------
    # STRUCTURED ANALYSIS
    # -----------------------------------------------------

    def test_structured_analysis():

        status, body = api_request(
            "POST",
            (
                f"/stocks/"
                f"{TEST_SYMBOL}"
                "/analyze/structured"
            ),
            token=user_token,
            timeout=AI_TIMEOUT
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "symbol"
            )
            == TEST_SYMBOL,
            "Structured symbol mismatch"
        )

        expect(
            body.get(
                "analysis_type"
            )
            == (
                "structured_stock_analysis"
            ),
            (
                "Unexpected structured "
                "analysis_type"
            )
        )

        required_sections = {
            "price_trend",
            "momentum",
            "volume",
            "volatility",
            "fundamentals",
            "news",
            "risks",
            "data_limits"
        }

        missing = (
            required_sections
            - set(
                body.keys()
            )
        )

        expect(
            not missing,
            (
                "Structured analysis missing "
                f"sections: {sorted(missing)}"
            )
        )


    run_test(
        "Structured stock AI analysis",
        test_structured_analysis
    )


    # -----------------------------------------------------
    # INVALID TICKER
    # -----------------------------------------------------

    def test_invalid_ticker():

        status, body = api_request(
            "POST",
            (
                f"/stocks/"
                f"{INVALID_SYMBOL}"
                "/analyze/structured"
            ),
            token=user_token,
            timeout=AI_TIMEOUT
        )

        expect_status(
            status,
            404,
            body
        )


    run_test(
        "Invalid ticker -> 404",
        test_invalid_ticker
    )


    def test_too_long_ticker():

        status, body = api_request(
            "POST",
            (
                f"/stocks/"
                f"{TOO_LONG_SYMBOL}"
                "/analyze/structured"
            ),
            token=user_token
        )

        expect_status(
            status,
            400,
            body
        )


    run_test(
        "Too-long ticker -> 400",
        test_too_long_ticker
    )


    # -----------------------------------------------------
    # ADMIN USER OPERATIONS
    # -----------------------------------------------------

    def test_admin_find_temp():

        status, body = api_request(
            "GET",
            "/admin/users",
            token=admin_token
        )

        expect_status(
            status,
            200,
            body
        )

        users = extract_list(
            body
        )

        matches = [
            item
            for item in users
            if (
                isinstance(
                    item,
                    dict
                )
                and item.get(
                    "id"
                )
                == temp_user_id
            )
        ]

        expect(
            len(
                matches
            )
            == 1,
            (
                "Temporary user not found "
                "in admin user list"
            )
        )


    run_test(
        "Admin can see temporary user",
        test_admin_find_temp
    )


    def test_invalid_role():

        status, body = api_request(
            "PATCH",
            (
                f"/admin/users/"
                f"{temp_user_id}/role"
            ),
            token=admin_token,
            json_body={
                "role": "superadmin"
            }
        )

        expect_status(
            status,
            422,
            body
        )


    run_test(
        "Invalid admin role -> 422",
        test_invalid_role
    )


    def test_promote_user():

        status, body = api_request(
            "PATCH",
            (
                f"/admin/users/"
                f"{temp_user_id}/role"
            ),
            token=admin_token,
            json_body={
                "role": "admin"
            }
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "role"
            )
            == "admin",
            (
                "User was not promoted: "
                f"{body}"
            )
        )


    run_test(
        "Admin promote user",
        test_promote_user
    )


    def test_restore_user_role():

        status, body = api_request(
            "PATCH",
            (
                f"/admin/users/"
                f"{temp_user_id}/role"
            ),
            token=admin_token,
            json_body={
                "role": "user"
            }
        )

        expect_status(
            status,
            200,
            body
        )

        expect(
            body.get(
                "role"
            )
            == "user",
            (
                "User role was not "
                f"restored: {body}"
            )
        )


    run_test(
        "Admin restore user role",
        test_restore_user_role
    )


    # -----------------------------------------------------
    # HISTORY DELETE
    # -----------------------------------------------------

    def test_delete_history():

        status, body = api_request(
            "DELETE",
            (
                f"/conversations/"
                f"{conversation_id}/history"
            ),
            token=user_token
        )

        expect_status(
            status,
            {
                200,
                204
            },
            body
        )


    run_test(
        "Delete conversation history",
        test_delete_history
    )


    def test_history_empty():

        status, body = api_request(
            "GET",
            (
                f"/conversations/"
                f"{conversation_id}/history"
            ),
            token=user_token
        )

        expect_status(
            status,
            200,
            body
        )

        items = extract_list(
            body
        )

        expect(
            len(
                items
            )
            == 0,
            (
                "History is not empty "
                "after deletion"
            )
        )


    run_test(
        "History empty after delete",
        test_history_empty
    )


    # -----------------------------------------------------
    # WATCHLIST DELETE
    # -----------------------------------------------------

    def test_watchlist_delete():

        status, body = api_request(
            "DELETE",
            (
                f"/watchlist/"
                f"{TEST_SYMBOL}"
            ),
            token=user_token
        )

        expect_status(
            status,
            {
                200,
                204
            },
            body
        )


    run_test(
        "Watchlist delete",
        test_watchlist_delete
    )

    watchlist_exists = False


    # -----------------------------------------------------
    # CONVERSATION DELETE
    # -----------------------------------------------------

    def test_conversation_delete():

        status, body = api_request(
            "DELETE",
            (
                f"/conversations/"
                f"{conversation_id}"
            ),
            token=user_token
        )

        expect_status(
            status,
            {
                200,
                204
            },
            body
        )


    run_test(
        "Conversation delete",
        test_conversation_delete
    )

    conversation_exists = False


    def test_deleted_conversation():

        status, body = api_request(
            "GET",
            (
                f"/conversations/"
                f"{conversation_id}"
            ),
            token=user_token
        )

        expect_status(
            status,
            404,
            body
        )


    run_test(
        "Deleted conversation -> 404",
        test_deleted_conversation
    )


    # -----------------------------------------------------
    # ADMIN DELETE TEMP USER
    # -----------------------------------------------------

    def test_admin_delete_user():

        status, body = api_request(
            "DELETE",
            (
                f"/admin/users/"
                f"{temp_user_id}"
            ),
            token=admin_token
        )

        expect_status(
            status,
            {
                200,
                204
            },
            body
        )


    run_test(
        "Admin delete temporary user",
        test_admin_delete_user
    )

    temp_user_exists = False


    # -----------------------------------------------------
    # LOGIN AFTER DELETE MUST FAIL
    # -----------------------------------------------------

    def test_deleted_user_login():

        status, body = api_request(
            "POST",
            "/login",
            form_body={
                "username": temp_username,
                "password": temp_password
            }
        )

        expect_status(
            status,
            401,
            body
        )


    run_test(
        "Deleted user cannot login",
        test_deleted_user_login
    )


# =========================================================
# SUMMARY
# =========================================================

def print_summary():

    print()
    print(
        "=" * 68
    )

    print(
        "FINAL REGRESSION SUMMARY"
    )

    print(
        "=" * 68
    )


    passed = sum(
        1
        for _, ok, _, _ in results
        if ok
    )

    failed = sum(
        1
        for _, ok, _, _ in results
        if not ok
    )


    for (
        name,
        ok,
        duration,
        error
    ) in results:

        state = (
            "PASS"
            if ok
            else "FAIL"
        )

        print(
            f"[{state}] "
            f"{name:<42} "
            f"{duration:>7.2f}s"
        )

        if error:

            print(
                f"       {error}"
            )


    print()
    print(
        f"TOTAL : {len(results)}"
    )

    print(
        f"PASSED: {passed}"
    )

    print(
        f"FAILED: {failed}"
    )

    print()


    if failed == 0:

        print(
            "FINAL RESULT: PASS"
        )

    else:

        print(
            "FINAL RESULT: FAIL"
        )


    print(
        "=" * 68
    )


    return failed


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    try:

        main()


    except KeyboardInterrupt:

        print()
        print(
            "Regression test interrupted."
        )


    except Exception as exc:

        print()
        print(
            "[CRITICAL FAILURE]"
        )

        print(
            str(
                exc
            )
        )


    finally:

        if (
            temp_user_exists
            or conversation_exists
            or watchlist_exists
        ):

            emergency_cleanup()


        failed = print_summary()


    sys.exit(
        1
        if failed
        else 0
    )