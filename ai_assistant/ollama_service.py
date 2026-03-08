"""
Ollama API Service for YouthHub AI Assistant.
Connects to a local Ollama instance running Qwen 2.5.
"""
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Default Ollama configuration
OLLAMA_BASE_URL = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_TIMEOUT = getattr(settings, 'OLLAMA_TIMEOUT', 120)

def get_default_model():
    return getattr(settings, 'OLLAMA_MODEL', 'sailor2:1b')


# ────────────────────────────────────────────────────────────
# PROMPT TEMPLATES
# ────────────────────────────────────────────────────────────
PROMPTS = {
    'KẾ HOẠCH / BÁO CÁO': """Bạn là trợ lý soạn thảo văn bản hành chính cho tổ chức Đoàn - Hội Sinh viên.
Hãy soạn một BẢN KẾ HOẠCH / BÁO CÁO hoàn chỉnh theo cấu trúc chuẩn văn bản hành chính Việt Nam.

Thông tin:
- Tên sự kiện: {event_name}
- Tổ chức: {organization}
- Mô tả ngắn: {description}
- Ngày: {date}

Yêu cầu:
1. Tiêu đề rõ ràng, đúng định dạng.
2. Các mục: Mục đích & Ý nghĩa, Thời gian & Địa điểm, Nội dung chương trình, Công tác chuẩn bị, Dự trù kinh phí.
3. Văn phong trang trọng, chính xác.
4. Ghi rõ đơn vị tổ chức và đơn vị phối hợp.

Soạn văn bản:""",

    'BIÊN BẢN HỌP': """Bạn là trợ lý soạn thảo văn bản hành chính cho tổ chức Đoàn - Hội Sinh viên.
Hãy soạn một BIÊN BẢN HỌP hoàn chỉnh.

Thông tin:
- Tên cuộc họp: {event_name}
- Tổ chức: {organization}
- Mô tả ngắn: {description}
- Ngày: {date}

Yêu cầu:
1. Ghi rõ thời gian, địa điểm, thành phần tham dự.
2. Nội dung cuộc họp (các vấn đề thảo luận).
3. Kết luận và phân công nhiệm vụ.
4. Người ghi biên bản và chủ tọa ký tên.

Soạn biên bản:""",

    'TỜ TRÌNH': """Bạn là trợ lý soạn thảo văn bản hành chính cho tổ chức Đoàn - Hội Sinh viên.
Hãy soạn một TỜ TRÌNH hoàn chỉnh.

Thông tin:
- Nội dung trình: {event_name}
- Tổ chức: {organization}
- Mô tả ngắn: {description}
- Ngày: {date}

Yêu cầu:
1. Kính gửi đúng cấp trên.
2. Căn cứ pháp lý hoặc thực tiễn.
3. Nội dung đề xuất chi tiết.
4. Kiến nghị cụ thể.

Soạn tờ trình:""",

    'CÔNG VĂN': """Bạn là trợ lý soạn thảo văn bản hành chính cho tổ chức Đoàn - Hội Sinh viên.
Hãy soạn một CÔNG VĂN hoàn chỉnh.

Thông tin:
- Chủ đề: {event_name}
- Tổ chức: {organization}
- Mô tả ngắn: {description}
- Ngày: {date}

Yêu cầu:
1. Số hiệu công văn, ngày tháng.
2. Kính gửi đúng đối tượng.
3. Nội dung ngắn gọn, rõ ràng.
4. Nơi nhận, ký tên.

Soạn công văn:""",

    'BÀI ĐĂNG SOCIAL': """Bạn là chuyên viên truyền thông cho tổ chức Đoàn - Hội Sinh viên trường Đại học.
Hãy viết một BÀI ĐĂNG MẠNG XÃ HỘI (Facebook Fanpage) thật thu hút, năng động và chuyên nghiệp.

Thông tin:
- Tên sự kiện/chủ đề: {event_name}
- Tổ chức: {organization}
- Mô tả ngắn: {description}
- Ngày: {date}

Yêu cầu:
1. Mở bài ấn tượng, có chứa emoji phù hợp với sinh viên trẻ trung.
2. Thân bài truyền tải rõ ràng thời gian, địa điểm, quyền lợi tham gia.
3. Kêu gọi hành động (Call to Action) mạnh mẽ (like, share, tag bạn bè, điền form...).
4. Đoạn cuối có hashtag phù hợp (ví dụ: #DoanHoi, #SinhVien, #... ).
5. Câu chữ không quá cứng nhắc nhưng vẫn giữ được sự lịch sự của một tổ chức chính thống.

Viết bài đăng:""",

    'EMAIL THÔNG BÁO': """Bạn là trợ lý truyền thông cho tổ chức Đoàn - Hội Sinh viên.
Hãy soạn một EMAIL THÔNG BÁO gửi đến toàn thể sinh viên.

Thông tin:
- Tên sự kiện: {event_name}
- Tổ chức: {organization}
- Mô tả ngắn: {description}
- Ngày: {date}

Yêu cầu:
1. Tiêu đề email ngắn gọn, rõ ràng [THÔNG BÁO] ...
2. Mở đầu lịch sự (Kính gửi toàn thể các bạn sinh viên thân mến / Dear students, ...).
3. Đưa thông tin trọng tâm (Lý do email, thời gian, địa điểm, nội dung).
4. Nhấn mạnh hạn chót (deadline) đăng ký hoặc tham gia nếu có.
5. Lời chúc và thông tin liên hệ giải đáp thắc mắc.

Soạn email:""",

    'KỊCH BẢN MC': """Bạn là một MC chuyên nghiệp chuyên dẫn các chương trình của Đoàn - Hội Sinh viên.
Hãy soạn một KỊCH BẢN MC chi tiết cho sự kiện.

Thông tin:
- Tên sự kiện: {event_name}
- Tổ chức: {organization}
- Mô tả ngắn về luồng chương trình: {description}
- Ngày: {date}

Yêu cầu:
1. Bố cục rõ ràng: Tuyên bố lý do, Giới thiệu đại biểu, Khai mạc, Nội dung chính, Bế mạc.
2. Tại mỗi phần phải ghi rõ ràng [MC nam], [MC nữ], hoặc [MC] nếu dẫn đơn.
3. Lời dẫn phải trau chuốt, trang trọng đối với đại biểu nhưng phải tràn đầy năng lượng, nhiệt huyết đối với sinh viên.
4. Có những khoảng trống dự phòng "[Tùy cơ ứng biến]" hoặc "[Xin mời đại biểu X bước lên sân khấu...]"

Soạn kịch bản MC:""",
}


def check_ollama_status() -> dict:
    """Check if Ollama is running and the model is available."""
    default_model = get_default_model()
    try:
        resp = requests.get(f'{OLLAMA_BASE_URL}/api/tags', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = [m['name'] for m in data.get('models', [])]
            has_model = default_model in models or f"{default_model}:latest" in models
            return {
                'online': True,
                'models': models,
                'has_model': has_model,
            }
    except requests.ConnectionError:
        pass
    except Exception as e:
        logger.warning(f"Ollama check error: {e}")
    return {'online': False, 'models': [], 'has_model': False}


def generate_document(doc_type: str, event_name: str, organization: str, date: str, description: str = '', model_name: str = None) -> dict:
    """
    Generate a document using Ollama API.
    Returns dict with 'content', 'tokens_input', 'tokens_output', 'model', 'error'.
    """
    target_model = model_name or get_default_model()
    
    # Build prompt
    template = PROMPTS.get(doc_type, PROMPTS['KẾ HOẠCH / BÁO CÁO'])
    prompt = template.format(
        event_name=event_name or 'Chưa có tên',
        organization=organization or 'Đoàn Thanh niên',
        description=description or 'Không có mô tả thêm',
        date=date or 'Chưa xác định',
    )
    
    # Định dạng nghiêm ngặt để cấm Markdown và bắt buộc xuất Plain Text
    prompt += "\n\n=== QUY TẮC ĐỊNH DẠNG TỬ THI ===\n"
    prompt += "1. CHỈ XUẤT VĂN BẢN TRƠN (PLAIN TEXT).\n"
    prompt += "2. CẤM TUYỆT ĐỐI các ký tự đặc biệt của Markdown: dấu sao (*), dấu thăng (#), gạch ngang đầu dòng (-), dấu huyền (`), gạch dưới (_).\n"
    prompt += "3. KHÔNG sử dụng in đậm, in nghiêng bằng ký hiệu. Các đề mục lớn hãy VIẾT HOA TOÀN BỘ.\n"
    prompt += "4. Các danh sách thì đánh số kiểu 1. 2. 3. hoặc a. b. c. theo sau là dấu chấm.\n"
    prompt += "5. Đi thẳng vào nội dung chính, không chào hỏi, không lặp lại yêu cầu."

    try:
        resp = requests.post(
            f'{OLLAMA_BASE_URL}/api/generate',
            json={
                'model': target_model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.3,   # Lower for more precise/formal text
                    'top_p': 0.85,
                    'top_k': 40,
                    'num_predict': 2048,
                    'repeat_penalty': 1.1, # 1.25 is too extreme and causes gibberish
                },
            },
            timeout=OLLAMA_TIMEOUT,
        )

        if resp.status_code == 200:
            data = resp.json()
            return {
                'content': data.get('response', ''),
                'tokens_input': data.get('prompt_eval_count', 0),
                'tokens_output': data.get('eval_count', 0),
                'model': target_model,
                'error': None,
            }
        else:
            return {
                'content': '',
                'error': f'Ollama returned status {resp.status_code}: {resp.text[:200]}',
                'status_code': resp.status_code
            }

    except requests.ConnectionError:
        return {
            'content': '',
            'error': 'Không thể kết nối Ollama. Vui lòng chạy: ollama serve',
        }
    except requests.Timeout:
        return {
            'content': '',
            'error': f'Ollama timeout sau {OLLAMA_TIMEOUT}s. Model có thể đang tải.',
        }
    except Exception as e:
        logger.error(f"Ollama generate error: {e}")
        return {
            'content': '',
            'error': str(e),
        }


def generate_fallback(doc_type: str, event_name: str, organization: str, date: str, description: str = '') -> str:
    """Fallback template when Ollama is offline."""
    return f"""[BẢN MẪU — OLLAMA ĐANG OFFLINE]

{doc_type.upper()}

═══════════════════════════════════════════════
TÊN: {event_name or '...'}
TỔ CHỨC: {organization or '...'}
NGÀY: {date or '...'}
═══════════════════════════════════════════════

I. MỤC ĐÍCH & Ý NGHĨA
- [Điền mục đích chính của chương trình]
- [Ý nghĩa đối với sinh viên và tổ chức]

II. THỜI GIAN & ĐỊA ĐIỂM
- Thời gian: [Giờ bắt đầu] - [Giờ kết thúc] ngày {date or '...'}
- Địa điểm: [Tên địa điểm]

III. NỘI DUNG CHƯƠNG TRÌNH
1. [Nội dung thứ nhất]
2. [Nội dung thứ hai]
3. [Nội dung thứ ba]

IV. CÔNG TÁC CHUẨN BỊ
- Ban tổ chức: [Phân công]
- Truyền thông: [Kế hoạch truyền thông]
- Hậu cần: [Danh sách cần chuẩn bị]

V. DỰ TRÙ KINH PHÍ
- [Hạng mục 1]: ... VNĐ
- [Hạng mục 2]: ... VNĐ
- TỔNG: ... VNĐ

═══════════════════════════════════════════════
LƯU Ý: Đây là bản mẫu. Hãy khởi động Ollama
để AI tạo văn bản tự động.
Chạy: ollama serve && ollama run qwen2.5:7b
═══════════════════════════════════════════════"""
