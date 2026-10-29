import re
import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# fenced_code (without codehilite) emits: <pre><code class="language-yaml">…</code></pre>
_CODE_RE = re.compile(r'<pre><code(?: class="language-(?P<lang>[\w+#-]+)")?>(?P<code>[\s\S]*?)</code></pre>')

_COPY_ICON = (
    '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" '
    'viewBox="0 0 24 24" aria-hidden="true">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2"/>'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M14 10h4a2 2 0 012 2v8a2 2 0 01-2 2h-8a2 2 0 01-2-2v-4"/>'
    '</svg>'
)


@register.filter
def render_post_body(value):
    """Render a post section as Markdown, wrapping fenced code blocks in a
    labelled panel with a one-click Copy button."""
    if not value:
        return ''

    html = markdown.markdown(value, extensions=['fenced_code', 'tables'])

    def wrap(match):
        lang = match.group('lang') or 'code'
        code = match.group('code')
        return (
            '<div class="code-block my-6 rounded-xl overflow-hidden border border-zinc-700">'
            '<div class="flex items-center justify-between px-4 py-2 bg-zinc-800/80 border-b border-zinc-700">'
            f'<span class="text-xs font-mono text-zinc-400 uppercase tracking-wider">{lang}</span>'
            f'<button type="button" class="copy-btn flex items-center gap-1.5 text-xs font-mono text-zinc-300 '
            f'hover:text-amber-400 transition-colors" aria-label="Copy {lang} code to clipboard">'
            f'{_COPY_ICON}<span class="copy-label">Copy</span>'
            '</button></div>'
            '<pre class="bg-zinc-950 p-4 overflow-x-auto text-sm leading-relaxed" tabindex="0">'
            f'<code class="font-mono text-zinc-100 whitespace-pre">{code}</code></pre>'
            '</div>'
        )

    return mark_safe(_CODE_RE.sub(wrap, html))
