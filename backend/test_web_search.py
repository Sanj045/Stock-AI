from ai.web_search import (
    search_news_candidates,
)


TITLE = (
    "FPT: Quy\u1ebft \u0111\u1ecbnh "
    "c\u1ee7a Ch\u1ee7 t\u1ecbch H\u0110QT "
    "v\u1ec1 vi\u1ec7c th\u00f4ng qua "
    "ph\u01b0\u01a1ng \u00e1n ph\u00e1t "
    "h\u00e0nh c\u1ed5 phi\u1ebfu "
    "\u0111\u1ec3 t\u0103ng v\u1ed1n "
    "c\u1ed5 ph\u1ea7n t\u1eeb NVCSH"
)


results = search_news_candidates(
    symbol="FPT",
    title=TITLE,
    publish_time=(
        "2026-09-10T18:11:16"
    ),
    max_results=5,
)


print()
print(
    "===== SEARCH INPUT ====="
)

print(
    "TITLE:",
    TITLE,
)

print()
print(
    "===== RESULTS ====="
)

print(
    "COUNT:",
    len(results),
)


for index, item in enumerate(
    results,
    start=1,
):
    print()

    print(
        f"[{index}]"
    )

    print(
        "TITLE:",
        item.title,
    )

    print(
        "URL:",
        item.url,
    )

    print(
        "DOMAIN:",
        item.source_domain,
    )

    print(
        "TRUSTED:",
        item.trusted_source,
    )

    print(
        "TAVILY SCORE:",
        item.score,
    )

    print(
        "LOCAL RELEVANCE:",
        item.relevance_score,
    )

    print(
        "CONTENT:",
        (
            item.content[:300]
            if item.content
            else None
        ),
    )