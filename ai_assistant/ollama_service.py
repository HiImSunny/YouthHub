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
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5-coder:1.5b')
OLLAMA_TIMEOUT = getattr(settings, 'OLLAMA_TIMEOUT', 120)


# ────────────────────────────────────────────────────────────
# PROMPT TEMPLATES
# ────────────────────────────────────────────────────────────
PROMPTS = {
    'KẾ HOẠCH / BÁO CÁO': """Bạn là trợ lý soạn thảo văn bản hành chính cho tổ chức Đoàn - Hội Sinh viên.
Hãy soạn một BẢN KẾ HOẠCH / BÁO CÁO hoàn chỉnh theo cấu trúc chuẩn văn bản hành chính Việt Nam.

Thông tin:
- Tên sự kiện: {event_name}
- Tổ chức: {organization}
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
- Ngày: {date}

Yêu cầu:
1. Số hiệu công văn, ngày tháng.
2. Kính gửi đúng đối tượng.
3. Nội dung ngắn gọn, rõ ràng.
4. Nơi nhận, ký tên.

Soạn công văn:""",
}


def check_ollama_status() -> dict:
    """Check if Ollama is running and the model is available."""
    try:
        resp = requests.get(f'{OLLAMA_BASE_URL}/api/tags', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = [m['name'] for m in data.get('models', [])]
            return {
                'online': True,
                'models': models,
                'has_model': OLLAMA_MODEL in models or any(OLLAMA_MODEL.split(':')[0] in m for m in models),
            }
    except requests.ConnectionError:
        pass
    except Exception as e:
        logger.warning(f"Ollama check error: {e}")
    return {'online': False, 'models': [], 'has_model': False}


def generate_document(doc_type: str, event_name: str, organization: str, date: str) -> dict:
    """
    Generate a document using Ollama API.
    Returns dict with 'content', 'tokens_input', 'tokens_output', 'model', 'error'.
    """
    # Build prompt
    template = PROMPTS.get(doc_type, PROMPTS['KẾ HOẠCH / BÁO CÁO'])
    prompt = template.format(
        event_name=event_name or 'Chưa có tên',
        organization=organization or 'Đoàn Thanh niên',
        date=date or 'Chưa xác định',
    )

    try:
        resp = requests.post(
            f'{OLLAMA_BASE_URL}/api/generate',
            json={
                'model': OLLAMA_MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'num_predict': 2048,
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
                'model': OLLAMA_MODEL,
                'error': None,
            }
        else:
            return {
                'content': '',
                'error': f'Ollama returned status {resp.status_code}: {resp.text[:200]}',
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


def generate_fallback(doc_type: str, event_name: str, organization: str, date: str) -> str:
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
