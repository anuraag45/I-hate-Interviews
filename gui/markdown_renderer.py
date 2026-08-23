import re
import html

def render_markdown_to_qt_html(text: str, accent_color: str = "#F6D860", text_color: str = "#F0F2F7", bg_card: str = "#181C26", font_size: int = 13) -> str:
    """
    Converts LLM markdown output into rich, readable, stylized HTML for Qt QLabel.
    Supports code blocks with dark surfaces, bold highlights, bullet points, and math symbols.
    """
    if not text:
        return ""

    # Check for placeholder states
    if any(p in text for p in ["Ready to extract", "Baseline vs. optimal", "Production code specification", "Ready for next topic", "Architecture breakdown", "Code implementation"]):
        return f'<div style="color: #8E95A5; font-style: italic; font-size: {font_size}px; line-height: 1.4;">{html.escape(text)}</div>'

    # 1. Process Code Blocks
    def code_replacer(match):
        lang = match.group(1) or ""
        code_body = match.group(2)
        escaped_code = html.escape(code_body.strip())
        
        # Simple Python keyword highlighting
        keywords = ["def ", "class ", "return ", "if ", "else:", "elif ", "for ", "in ", "while ", "import ", "from ", "try:", "except ", "with ", "yield "]
        for kw in keywords:
            escaped_code = escaped_code.replace(kw, f'<span style="color: #F6D860; font-weight: bold;">{kw}</span>')
        
        # Highlight comments
        escaped_code = re.sub(r'(#[^\n]+)', r'<span style="color: #718096; font-style: italic;">\1</span>', escaped_code)

        return f'''
        <div style="background-color: #0E1118; border: 1px solid rgba(255, 255, 255, 0.12); border-left: 3px solid {accent_color}; border-radius: 6px; padding: 8px 10px; margin: 6px 0; font-family: Consolas, 'Fira Code', Monaco, monospace; font-size: {max(10, font_size - 1.5):.1f}px; color: #E2E8F0; white-space: pre-wrap;">
        {escaped_code}
        </div>
        '''

    processed = re.sub(r'```([a-zA-Z0-9_-]*)\n(.*?)```', code_replacer, text, flags=re.DOTALL)

    # 2. Process Inline Code `code`
    processed = re.sub(r'`([^`]+)`', rf'<code style="background-color: #1E2332; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 1px 4px; font-family: Consolas, monospace; font-size: {max(10, font_size - 1):.1f}px; color: {accent_color};">\1</code>', processed)

    # 3. Process Bold **text**
    processed = re.sub(r'\*\*([^*]+)\*\*', rf'<strong style="color: {accent_color}; font-weight: 700;">\1</strong>', processed)

    # 4. Process Bullet Points
    lines = processed.split("\n")
    formatted_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("•") or stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped.lstrip("•-* ").strip()
            formatted_lines.append(f'<div style="margin: 3px 0 3px 6px; line-height: 1.45;"><span style="color: {accent_color}; font-weight: bold; margin-right: 6px;">•</span><span style="color: {text_color}; font-size: {font_size}px;">{content}</span></div>')
        elif stripped.startswith("#"):
            h_text = stripped.lstrip("#").strip()
            formatted_lines.append(f'<div style="color: {accent_color}; font-weight: 800; font-size: {font_size + 1}px; margin: 6px 0 3px 0;">{h_text}</div>')
        elif stripped:
            formatted_lines.append(f'<div style="color: {text_color}; font-size: {font_size}px; line-height: 1.45; margin: 2px 0;">{stripped}</div>')
        else:
            formatted_lines.append('<div style="height: 4px;"></div>')

    final_html = "".join(formatted_lines)
    return f'<div style="font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;">{final_html}</div>'
