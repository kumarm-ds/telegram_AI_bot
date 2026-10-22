"""Local-only, model-aware manual retrieval. No internet or external search."""
from dataclasses import dataclass
from pathlib import Path
import re
from pypdf import PdfReader
from docx import Document

@dataclass(frozen=True)
class Passage:
    source: str
    page: str
    text: str

STOP = set('a an and are as at be by can could do does for from how i in is it of on or our the their there these this to was were what when where which who why will with you your please about explain tell give describe terms details'.split())
TOPICS = {
    'warranty': ('warranty', 'guarantee', 'coverage', 'claim', 'covered', 'expiry', 'extended'),
    'troubleshooting': ('troubleshoot', 'troubleshooting', 'fault', 'error', 'alarm', 'problem', 'failure', 'diagnose', 'diagnostic'),
    'maintenance': ('maintenance', 'service interval', 'schedule', 'lubrication', 'inspection', 'preventive'),
    'installation': ('install', 'installation', 'commission', 'commissioning', 'setup', 'mounting'),
    'spare_parts': ('spare', 'replacement', 'part number', 'parts', 'component'),
    'safety': ('safety', 'hazard', 'lockout', 'tagout', 'ppe', 'danger', 'warning'),
    'faq': ('faq', 'frequently asked'),
    'service_bulletin': ('service bulletin', 'bulletin', 'recall', 'update'),
    'operator_quick_reference': ('operator', 'operate', 'operation', 'quick reference'),
    'product_manual': ('specification', 'specifications', 'capacity', 'rating', 'dimension', 'weight', 'power', 'technical data'),
}
MODEL_RE = re.compile(r'(?:^|_)(KTX-[A-Z0-9]+(?:-[A-Z0-9]+)*)(?=_)', re.I)

def words(text):
    return set(re.findall(r'[a-z0-9]{3,}', text.lower())) - STOP

def split_text(name, page, text):
    parts = text.split()
    return [Passage(name, str(page), ' '.join(parts[i:i + 210]))
            for i in range(0, len(parts), 170) if parts[i:i + 210]]

def load_manuals(folder='manuals'):
    passages = []
    root = Path(folder)
    if not root.is_dir():
        return passages
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.name.lower().startswith(('_index', 'index.')):
            continue
        try:
            if path.suffix.lower() == '.pdf':
                for n, page in enumerate(PdfReader(str(path)).pages, 1):
                    passages.extend(split_text(path.name, n, page.extract_text() or ''))
            elif path.suffix.lower() == '.docx':
                doc = Document(str(path))
                passages.extend(split_text(path.name, 'document', '\n'.join(p.text for p in doc.paragraphs)))
            elif path.suffix.lower() in ('.txt', '.md'):
                passages.extend(split_text(path.name, 'document', path.read_text(encoding='utf-8-sig')))
        except Exception as exc:
            print(f'WARNING: Could not read {path.name}: {exc}', flush=True)
    return passages

def _models(passages):
    # Model IDs are taken from filenames, never inferred from external sources.
    result = set()
    for p in passages:
        match = MODEL_RE.search(p.source)
        if match:
            result.add(match.group(1).upper())
    return result

def _requested_model(question, passages):
    normalized = re.sub(r'[^A-Z0-9]', '', question.upper())
    matches = [m for m in _models(passages)
               if re.sub(r'[^A-Z0-9]', '', m) in normalized
               or re.sub(r'[^A-Z0-9]', '', m.removeprefix('KTX-')) in normalized]
    # A model is unambiguous only if exactly one known model is mentioned.
    return matches[0] if len(matches) == 1 else None

def search(question, passages, count=6):
    query = words(question)
    if not query:
        return []
    model = _requested_model(question, passages)
    normalized_question = question.lower()
    topics = [topic for topic, aliases in TOPICS.items()
              if any(alias in normalized_question for alias in aliases)]
    ranked = []
    for passage in passages:
        source = passage.source.lower()
        if model and model.lower() not in source.replace('_', '-'):
            # Hard model filter: never blend documents from another product.
            continue
        content_words = words(passage.text)
        filename_words = words(source.replace('_', ' ').replace('-', ' '))
        overlap = len(query & content_words)
        filename_overlap = len(query & filename_words)
        topic_bonus = max((8 for topic in topics if topic in source), default=0)
        # A filename matching the requested document type is highly relevant.
        score = overlap * 2 + filename_overlap * 2 + topic_bonus
        if score > 0:
            ranked.append((score, overlap, passage))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [p for _, _, p in ranked[:count]]
