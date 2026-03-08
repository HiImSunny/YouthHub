# Task Plan

1. Add timing calculation to `ai_assistant/views.py` inside `generate_view`.
2. Send `generation_time` down via context.
3. Replace the text '█▒▒▒▒▒▒▒▒▒ 10%' in `chat.html` `aiLoadingStart()` with a live `setInterval` timer counting seconds.
4. Modify `chat.html` template to show a temporary success alert or change the button text with the generation time if `generation_time` is available on page load.
