from __future__ import annotations
import yaml

def to_markdown(front_matter: dict, pages: list[str]) -> str:
    header = yaml.safe_dump(front_matter, sort_keys=False, allow_unicode=True).strip()
    body=[]
    for i, page in enumerate(pages, 1): body.append(f"<!-- page: {i} -->\n# Page {i}\n\n{page.strip()}\n")
    return f"---\n{header}\n---\n\n" + "\n".join(body)

def split_pages(markdown: str):
    import re
    return [(int(n), body) for n, body in re.findall(r"<!-- page: (\d+) -->\s*# Page \d+\s*(.*?)(?=<!-- page:|\Z)", markdown, re.S)]

