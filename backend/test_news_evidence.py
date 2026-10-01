from ai.news_evidence import (
    resolve_news_evidence,
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


result = resolve_news_evidence(
    symbol="FPT",
    title=TITLE,
    publish_time=(
        "2026-09-10T18:11:16"
    ),
    original_url=(
        "https://www.kbsec.com.vn/"
        "2026/09/"
        "fpt-quyet-dinh-cua-chu-tich-hdqt-"
        "ve-viec-thong-qua-phuong-an-phat-"
        "hanh-co-phieu-de-tang-von-co-phan-"
        "tu-nvcsh-214-1491116.htm"
    ),
    original_source="KBS",
)


print()
print(
    "===== EVIDENCE RESULT ====="
)

print(
    result
)

if result:
    print()

    print(
        "URL:",
        result.url,
    )

    print(
        "SOURCE:",
        result.source,
    )

    print(
        "METHOD:",
        result.method,
    )

    print(
        "VERIFIED:",
        result.verified,
    )