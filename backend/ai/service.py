import json
import time

from json import JSONDecodeError

from google import genai

from google.genai import types

from google.genai.errors import (
    ServerError
)

from pydantic import (
    ValidationError
)

from ai.schemas import (
    StructuredStockAnalysis
)

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_FALLBACK_MODEL
)

from logger import logger


# =========================================================
# CONFIG / CLIENT
# =========================================================

if not GEMINI_API_KEY:

    raise RuntimeError(
        "GEMINI_API_KEY is not configured"
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================================================
# CUSTOM EXCEPTIONS
# =========================================================

class StructuredOutputError(
    RuntimeError
):
    """
    Raised when Gemini responds successfully at the HTTP level
    but the structured payload cannot be safely validated.

    Examples:
    - empty response
    - invalid JSON
    - wrong schema
    - response.parsed has unexpected type

    This error is safe to use internally to decide whether
    the fallback model should be attempted.
    """

    pass


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
Bạn là AI hỗ trợ phân tích thông tin cổ phiếu.

Nguyên tắc bắt buộc:

1. Chỉ sử dụng dữ liệu được cung cấp trong context.
2. Không tự tạo dữ liệu còn thiếu.
3. Không giả định dữ liệu là dữ liệu thời gian thực nếu context
   không nói như vậy.
4. Phân biệt rõ dữ liệu thực tế và phần diễn giải.
5. Không khẳng định chắc chắn hướng giá tương lai.
6. Không đưa ra mệnh lệnh mua hoặc bán.
7. Không hứa hẹn lợi nhuận.
8. Nếu dữ liệu không đủ, phải nói rõ giới hạn dữ liệu.
9. Khi nguồn dữ liệu được đánh dấu unavailable/error/empty,
   không được tự bù dữ liệu cho nguồn đó.
10. Ưu tiên cách diễn đạt trung tính, rõ ràng và có thể truy vết
    về dữ liệu trong context.
""".strip()


# =========================================================
# NORMAL GENERATION
# =========================================================

def generate_with_model(
    model: str,
    prompt: str
) -> str:

    response = client.models.generate_content(
        model=model,

        contents=prompt,

        config=types.GenerateContentConfig(
            system_instruction=(
                SYSTEM_PROMPT
            ),
            temperature=0.4,
            max_output_tokens=1200
        )
    )


    text = response.text


    if not text:

        raise RuntimeError(
            "Gemini returned an empty response"
        )


    return text.strip()


# =========================================================
# NORMAL MODEL FALLBACK
# =========================================================

def _ask_with_fallback(
    prompt: str
) -> str:

    models = [
        GEMINI_MODEL,
        GEMINI_FALLBACK_MODEL
    ]


    last_exception = None


    for model in models:

        # Avoid attempting the exact same model twice
        # if both environment variables are identical.
        if (
            model != models[0]
            and model == models[0]
        ):
            continue


        for attempt in range(3):

            try:

                logger.info(
                    "Gemini request | "
                    "mode=text | "
                    "model=%s | "
                    "attempt=%s",
                    model,
                    attempt + 1
                )


                return generate_with_model(
                    model=model,
                    prompt=prompt
                )


            except ServerError as exc:

                last_exception = exc


                status_code = getattr(
                    exc,
                    "status_code",
                    None
                )


                if status_code != 503:

                    logger.exception(
                        "Gemini server error | "
                        "mode=text | "
                        "model=%s | "
                        "status=%s",
                        model,
                        status_code
                    )

                    raise


                logger.warning(
                    "Gemini temporarily unavailable | "
                    "mode=text | "
                    "model=%s | "
                    "attempt=%s/3",
                    model,
                    attempt + 1
                )


                if attempt < 2:

                    wait_time = (
                        2 ** attempt
                    )

                    time.sleep(
                        wait_time
                    )


    if last_exception is not None:
        raise last_exception


    raise RuntimeError(
        "No Gemini model was available"
    )


# =========================================================
# STRUCTURED GENERATION
# =========================================================

def generate_structured_with_model(
    model: str,
    prompt: str
) -> StructuredStockAnalysis:
    """
    Ask one Gemini model for a StructuredStockAnalysis.

    HTTP/service errors are allowed to propagate as ServerError.

    Content/schema problems are converted into
    StructuredOutputError so the fallback model can be tried.
    """

    response = client.models.generate_content(
        model=model,

        contents=prompt,

        config=types.GenerateContentConfig(
            system_instruction=(
                SYSTEM_PROMPT
            ),

            temperature=0.2,

            max_output_tokens=3000,

            response_mime_type=(
                "application/json"
            ),

            response_schema=(
                StructuredStockAnalysis
            )
        )
    )


    # -----------------------------------------------------
    # Preferred path: SDK already parsed the response
    # -----------------------------------------------------

    parsed = getattr(
        response,
        "parsed",
        None
    )


    if parsed is not None:

        try:

            if isinstance(
                parsed,
                StructuredStockAnalysis
            ):
                return parsed


            if isinstance(
                parsed,
                dict
            ):
                return (
                    StructuredStockAnalysis
                    .model_validate(
                        parsed
                    )
                )


            # Some SDK versions may expose another
            # Pydantic-like object.
            if hasattr(
                parsed,
                "model_dump"
            ):

                return (
                    StructuredStockAnalysis
                    .model_validate(
                        parsed.model_dump()
                    )
                )


            raise TypeError(
                "Unexpected parsed response type"
            )


        except (
            ValidationError,
            TypeError,
            ValueError
        ) as exc:

            raise StructuredOutputError(
                "Gemini parsed response failed "
                "structured validation"
            ) from exc


    # -----------------------------------------------------
    # Fallback parsing path: response.text
    # -----------------------------------------------------

    text = getattr(
        response,
        "text",
        None
    )


    if not text:

        raise StructuredOutputError(
            "Gemini returned an empty structured response"
        )


    try:

        raw = json.loads(
            text
        )


    except (
        JSONDecodeError,
        TypeError
    ) as exc:

        raise StructuredOutputError(
            "Gemini returned invalid structured JSON"
        ) from exc


    try:

        return (
            StructuredStockAnalysis
            .model_validate(
                raw
            )
        )


    except ValidationError as exc:

        raise StructuredOutputError(
            "Gemini structured JSON did not "
            "match the required schema"
        ) from exc


# =========================================================
# STRUCTURED MODEL FALLBACK
# =========================================================

def _ask_structured_with_fallback(
    prompt: str
) -> StructuredStockAnalysis:
    """
    Structured fallback policy:

    503:
        Retry the same model up to 3 times.
        If still unavailable, try fallback model.

    Invalid JSON/schema:
        Do not waste 3 retries on the same malformed response.
        Move directly to fallback model.

    Other unexpected exceptions:
        Propagate immediately instead of hiding programming or
        configuration errors.
    """

    models = []


    for candidate in (
        GEMINI_MODEL,
        GEMINI_FALLBACK_MODEL
    ):

        if (
            candidate
            and candidate not in models
        ):
            models.append(
                candidate
            )


    if not models:

        raise RuntimeError(
            "No Gemini model is configured"
        )


    last_exception = None


    for model in models:

        for attempt in range(3):

            try:

                logger.info(
                    "Gemini request | "
                    "mode=structured | "
                    "model=%s | "
                    "attempt=%s",
                    model,
                    attempt + 1
                )


                result = (
                    generate_structured_with_model(
                        model=model,
                        prompt=prompt
                    )
                )


                logger.info(
                    "Gemini structured response validated | "
                    "model=%s",
                    model
                )


                return result


            # -------------------------------------------------
            # Structured content/schema failure
            # -------------------------------------------------

            except StructuredOutputError as exc:

                last_exception = exc


                logger.warning(
                    "Gemini structured output invalid | "
                    "model=%s | "
                    "switching_to_fallback=true",
                    model
                )


                # A malformed schema is not a transport failure.
                # Move directly to the next model rather than
                # spending three calls on the same model.
                break


            # -------------------------------------------------
            # Gemini server error
            # -------------------------------------------------

            except ServerError as exc:

                last_exception = exc


                status_code = getattr(
                    exc,
                    "status_code",
                    None
                )


                if status_code != 503:

                    logger.exception(
                        "Gemini server error | "
                        "mode=structured | "
                        "model=%s | "
                        "status=%s",
                        model,
                        status_code
                    )

                    raise


                logger.warning(
                    "Gemini temporarily unavailable | "
                    "mode=structured | "
                    "model=%s | "
                    "attempt=%s/3",
                    model,
                    attempt + 1
                )


                if attempt < 2:

                    wait_time = (
                        2 ** attempt
                    )

                    time.sleep(
                        wait_time
                    )


                # attempt == 2:
                # loop ends and next model is tried.


    if last_exception is not None:

        raise last_exception


    raise RuntimeError(
        "Structured Gemini generation failed"
    )


# =========================================================
# GENERAL CHAT
# =========================================================

def ask_ai(
    message: str,
    history: list | None = None
) -> str:

    history = (
        history
        or []
    )


    history_text = ""


    if history:

        formatted_history = []


        for item in history:

            role = item.get(
                "role",
                "unknown"
            )


            content = item.get(
                "content",
                ""
            )


            formatted_history.append(
                f"{role}: {content}"
            )


        history_text = (
            "\n".join(
                formatted_history
            )
        )


    prompt = f"""
Lịch sử hội thoại:
{history_text or "Không có lịch sử trước đó."}

Tin nhắn hiện tại:
{message}

Hãy trả lời bằng tiếng Việt rõ ràng, ngắn gọn khi có thể.
""".strip()


    return _ask_with_fallback(
        prompt
    )


# =========================================================
# STOCK ANALYSIS RULES
# =========================================================

STOCK_ANALYSIS_RULES = """
QUY TẮC PHÂN TÍCH CỔ PHIẾU:

1. Chỉ dùng dữ liệu có trong STOCK_CONTEXT.

2. Tuân thủ metadata.data_rules trong STOCK_CONTEXT.

3. Không tự tạo field kỹ thuật mới.
   Ví dụ nếu context không có change_3d_pct thì không được
   tự suy ra hoặc đề cập change_3d_pct.

4. latest và price_history:
   - latest được backend suy ra từ phiên gần nhất.
   - price_history được sắp từ cũ đến mới.

5. Moving averages:
   - MA5 và MA20 chỉ là simple moving averages.
   - Giá nằm trên/dưới MA chỉ được mô tả như một thực tế.
   - Không coi riêng MA là tín hiệu mua/bán.
   - Không dùng MA để khẳng định hướng giá tương lai.

6. RSI:
   - RSI14 chỉ được mô tả theo số liệu có trong context.
   - Có thể nói RSI dưới/trên mốc tham chiếu kỹ thuật 50.
   - Không được suy luận rằng bên bán đang mạnh lên,
     yếu đi, kiệt sức hoặc thị trường sắp đảo chiều
     chỉ dựa trên RSI.

7. Volatility:
   - volatility_20d_pct là thống kê biến động lịch sử.
   - Không gọi thấp/trung bình/cao nếu context không có
     benchmark so sánh.

8. Volume:
   - volume_ratio_20d chỉ mô tả khối lượng tương đối.
   - Không suy luận dòng tiền thông minh, bắt đáy,
     hành vi nhà đầu tư, áp lực mua hoặc áp lực bán.

9. Price position:
   - high_20d và low_20d chỉ là mức cao/thấp trong
     khoảng quan sát.
   - Không gọi chúng là hỗ trợ, kháng cự, đáy hoặc đỉnh.
   - price_position_20d_pct chỉ mô tả vị trí trong biên độ.

10. Fundamentals:
    - Giữ nguyên period được nguồn dữ liệu cung cấp.
    - Period có hậu tố _alt là biến thể nguồn dữ liệu.
    - Không tự thêm đơn vị nếu context không cung cấp.
    - Không khẳng định provenance như "do doanh nghiệp công bố"
      nếu context chỉ nói dữ liệu đến từ nguồn dữ liệu.

11. Company:
    - key_person phải giữ đúng name/position từ context.
    - charter_capital_reported_value không có đơn vị xác định
      nếu metadata nói như vậy.

12. News:
    - Nếu summary_available=false thì không được tự viết
      tóm tắt nội dung bài báo.
    - Có thể mô tả chủ đề ở mức headline nếu tiêu đề hỗ trợ.
    - Nếu url_available=false thì URL phải được xem là unavailable.
    - Không tự tạo URL.

13. Partial failure:
    - Kiểm tra sources và data_limits.
    - Nếu một nguồn error/empty thì không được bịa dữ liệu
      cho nguồn đó.
    - Vẫn có thể phân tích các nguồn còn available.

14. Rủi ro:
    - Chỉ nêu các điểm lưu ý có evidence từ context.
    - Không biến một chỉ báo kỹ thuật đơn lẻ thành dự báo.

15. Không đưa ra mệnh lệnh mua/bán.
16. Không đảm bảo lợi nhuận.
17. Không khẳng định chắc chắn giá sẽ tăng hoặc giảm.
""".strip()


# =========================================================
# NORMAL STOCK ANALYSIS
# =========================================================

def analyze_stock(
    symbol: str,
    stock_context: str,
    question: str | None = None,
    history: list | None = None
) -> str:

    history = (
        history
        or []
    )


    history_text = ""


    if history:

        formatted_history = []


        for item in history:

            role = item.get(
                "role",
                "unknown"
            )


            content = item.get(
                "content",
                ""
            )


            formatted_history.append(
                f"{role}: {content}"
            )


        history_text = (
            "\n".join(
                formatted_history
            )
        )


    user_question = (
        question.strip()
        if (
            question
            and question.strip()
        )
        else (
            f"Hãy phân tích cổ phiếu {symbol} "
            "dựa trên dữ liệu được cung cấp."
        )
    )


    prompt = f"""
MÃ CỔ PHIẾU:
{symbol}

LỊCH SỬ HỘI THOẠI:
{history_text or "Không có lịch sử trước đó."}

CÂU HỎI:
{user_question}

STOCK_CONTEXT:
{stock_context}

{STOCK_ANALYSIS_RULES}

YÊU CẦU OUTPUT:

- Trả lời bằng tiếng Việt.
- Trình bày rõ dữ liệu thực tế trước rồi mới diễn giải.
- Nếu dữ liệu thiếu hoặc nguồn lỗi, nói rõ giới hạn.
- Không đưa ra khuyến nghị mua/bán trực tiếp.
""".strip()


    return _ask_with_fallback(
        prompt
    )


# =========================================================
# STRUCTURED STOCK ANALYSIS
# =========================================================

def analyze_stock_structured(
    symbol: str,
    stock_context: str
) -> dict:

    symbol = (
        symbol
        .strip()
        .upper()
    )


    prompt = f"""
MÃ CỔ PHIẾU:
{symbol}

STOCK_CONTEXT:
{stock_context}

{STOCK_ANALYSIS_RULES}

Hãy tạo một structured stock analysis đúng schema bắt buộc.

CÁC SECTION PHẢI CÓ:

1. price_trend
   - summary
   - facts
   - interpretation
   - Dùng latest, change_1d_pct, change_5d_pct,
     change_20d_pct, MA5, MA20, high_20d, low_20d,
     price_position_20d_pct khi chúng tồn tại.
   - Không gọi low_20d là hỗ trợ/đáy.
   - Không gọi high_20d là kháng cự/đỉnh.

2. momentum
   - Chủ yếu dùng RSI14 nếu có.
   - Chỉ mô tả RSI theo giá trị và mốc tham chiếu.
   - Không suy luận seller pressure hoặc reversal.

3. volume
   - Dùng latest volume, average_volume_20d
     và volume_ratio_20d nếu có.
   - Chỉ mô tả relative volume.
   - Không suy luận hành vi nhà đầu tư.

4. volatility
   - Dùng volatility_20d_pct nếu có.
   - Chỉ báo cáo thống kê.
   - Không gán nhãn low/moderate/high nếu không có benchmark.

5. fundamentals
   - Chỉ dùng fundamental fields thực sự có trong context.
   - Giữ đúng period.
   - Không tự tạo unit.
   - Không nói "do doanh nghiệp công bố" trừ khi context
     thực sự cung cấp provenance đó.

6. news
   - Dùng đúng headline metadata.
   - summary_available=false:
       không được tạo summary nội dung bài báo.
   - url_available=false:
       url phải null/unavailable.
   - Nếu source news error/empty:
       items phải để trống và nói rõ limitation.

7. risks
   - Chỉ đưa những điểm lưu ý có evidence trực tiếp từ context.
   - Evidence phải trỏ về dữ liệu hiện có.
   - Không biến technical observation thành prediction.

8. data_limits
   - Bao gồm các limitation quan trọng trong context.
   - Nêu rõ source nào unavailable nếu có.
   - Nêu các giới hạn kỹ thuật cần thiết.

YÊU CẦU CHUNG:

- symbol phải đúng là {symbol}.
- analysis_type phải là structured_stock_analysis.
- Không thêm section ngoài schema.
- Không tự tạo dữ liệu.
- Không đưa khuyến nghị mua hoặc bán.
- Không dự báo chắc chắn tương lai.
""".strip()


    result = (
        _ask_structured_with_fallback(
            prompt
        )
    )


    # -----------------------------------------------------
    # Final local sanity check
    # -----------------------------------------------------

    if (
        result.symbol
        .strip()
        .upper()
        != symbol
    ):

        raise StructuredOutputError(
            "Structured analysis returned "
            "an unexpected stock symbol"
        )


    return result.model_dump()