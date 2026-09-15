"""Generate the profile's tool chips, without API dependencies."""

from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "profile"
PALETTES = {
    "light": {"text": "1f2328", "muted": "59636e", "line": "d1d9e0", "accent": "0969da", "chip": "f6f8fa"},
    "dark": {"text": "f0f6fc", "muted": "a5aeb9", "line": "3d444d", "accent": "79c0ff", "chip": "151b23"},
}
TOOLS = {
    "languages": [("python", "Python", 61), ("sql", "SQL", 43), ("javascript", "JavaScript", 82), ("java", "Java", 48), ("dart", "Dart", 46)],
    "ai": [("pytorch", "PyTorch", 69), ("tensorflow", "TensorFlow", 90), ("hugging-face", "Hugging Face", 102), ("langgraph", "LangGraph", 86), ("pydantic-ai", "Pydantic AI", 86), ("langchain", "LangChain", 84)],
    "backend": [("fastapi", "FastAPI", 68), ("flask", "Flask", 52), ("docker", "Docker", 63), ("gcp", "GCP", 46), ("git", "Git", 36)],
}


def svg_document(width, height, title, content):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">\n'
        f'  <title id="title">{escape(title)}</title>\n'
        '  <g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif">\n'
        + content + '\n  </g>\n</svg>\n'
    )


def text(x, y, value, color, size=12, weight=400):
    return f'    <text x="{x}" y="{y}" fill="#{color}" font-size="{size}" font-weight="{weight}">{escape(value)}</text>'


def main():
    ASSETS.mkdir(exist_ok=True)
    chips = ASSETS / "tools"
    chips.mkdir(exist_ok=True)
    for theme, palette in PALETTES.items():
        for entries in TOOLS.values():
            for slug, label, width in entries:
                body = (
                    f'    <rect x=".5" y=".5" width="{width - 1}" height="23" rx="4" '
                    f'fill="#{palette["chip"]}" stroke="#{palette["line"]}"/>\n'
                    + text(9, 16, label, palette["text"])
                )
                (chips / f"{slug}-{theme}.svg").write_text(svg_document(width, 24, label, body))
    readme = ROOT / "README.md"
    content = readme.read_text()
    for group, entries in TOOLS.items():
        pictures = [
            '<picture><source media="(prefers-color-scheme: dark)" '
            f'srcset="./profile/tools/{slug}-dark.svg"><img '
            f'src="./profile/tools/{slug}-light.svg" alt="{escape(label)}" '
            f'height="24" width="{width}"></picture>'
            for slug, label, width in entries
        ]
        replacement = f'<!-- TOOLS:{group} -->\n<p>\n' + "\n".join(pictures) + f'\n</p>\n<!-- /TOOLS:{group} -->'
        content, count = re.subn(f'<!-- TOOLS:{group} -->.*?<!-- /TOOLS:{group} -->', replacement, content, flags=re.S)
        if count != 1:
            raise ValueError(f"Missing or duplicate tool section: {group}")
    readme.write_text(content)


if __name__ == "__main__":
    main()
