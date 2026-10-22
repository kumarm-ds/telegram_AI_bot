"""Local manual extraction and conservative retrieval. No external general search."""
from dataclasses import dataclass
from pathlib import Path
import re
from io import BytesIO
from pypdf import PdfReader
from docx import Document

@dataclass(frozen=True)
class Passage:
    source: str
    page: str
    text: str

STOP = set('a an and are as at be by can could do does for from how i in is it of on or our the their there these this to was were what when where which who why will with you your please about'.split())

def words(text):
    return set(re.findall(r'[a-z0-9]{3,}', text.lower())) - STOP

def split_text(name, page, text):
    parts = text.split()
    return [Passage(name, str(page), ' '.join(parts[i:i+210])) for i in range(0, len(parts), 170) if parts[i:i+210]]

def load_manuals(folder='manuals'):
    passages = []
    for path in sorted(Path(folder).iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        try:
            if suffix == '.pdf':
                reader = PdfReader(str(path))
                for page_num, page in enumerate(reader.pages, 1):
                    passages.extend(split_text(path.name, page_num, page.extract_text() or ''))
            elif suffix == '.docx':
                doc = Document(str(path))
                passages.extend(split_text(path.name, 'document', '\n'.join(p.text for p in doc.paragraphs)))
            elif suffix in ('.txt', '.md'):
                passages.extend(split_text(path.name, 'document', path.read_text(encoding='utf-8')))
        except Exception as exc:
            print(f'WARNING: Could not read {path.name}: {exc}', flush=True)
    return passages

def search(question, passages, count=5):
    query = words(question)
    if not query:
        return []
    results = []
    for passage in passages:
        match = len(query & words(passage.text))
        if match:
            results.append((match / len(query), match, passage))
    results.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [p for _, _, p in results[:count]]
