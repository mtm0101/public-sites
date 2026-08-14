"""Import DOL's IELTS vocabulary-by-band tables as four topic-grouped lessons."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from urllib.request import Request, urlopen
from urllib.parse import quote


SOURCE_URL = "https://www.dolenglish.vn/blog/tu-vung-tieng-anh-thong-dung#section-5"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "codex" / "dol"
OLD_COMBINED_OUTPUT = OUTPUT_DIR / (
    "dol-gpt-codex-speaking-2026-03-dol-ielts-vocabulary-by-band.json"
)
BANDS = (
    ("Band 4 – 5 (B1)", "b1", 4),
    ("Band 6 – 6.5 (B2)", "b2", 6),
    ("Band 7 – 7.5 (C1)", "c1", 7),
    ("Band 8+ (C2)", "c2", 8),
)

# Rules intentionally combine English headwords/definitions and accent-free Vietnamese
# meanings. The order handles specific everyday topics before abstract vocabulary.
TOPIC_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Travel & Transport", (
        r"\b(?:abroad|accommodation|airport|airline|aircraft|aeroplane|helicopter|flight|fly|journey|trip|travel|tour|touris\w*|holiday|hotel|hostel|passport|luggage|suitcase|destination|depart|departure|arrive|arrival|vehicle|transport|traffic|road|street|route|rail|train|bus|coach|taxi|car|truck|lorry|bicycle|bike|motorcycle|ship|boat|ferry|commute|voyage|expedition)\b",
        r"\b(?:du lich|nuoc ngoai|cho o|san bay|may bay|hanh trinh|ky nghi|khach san|ho chieu|hanh ly|diem den|khoi hanh|phuong tien|giao thong|duong pho|tau hoa|xe buyt|xe hoi|xe dap|tau thuyen)\b",
    )),
    ("Home & Daily Life", (
        r"\b(?:home|house|housing|household|room|bedroom|bathroom|kitchen|basement|downstairs|upstairs|door|window|wall|roof|floor|garden|furniture|chair|table|bed|sofa|fridge|refrigerator|oven|domestic|neighbou?rhood|resident|residence|abode|rent|routine|chores?)\b",
        r"\b(?:nha|cho o|phong|phong ngu|phong tam|phong bep|tang ham|tang duoi|cua|mai nha|san vuon|noi that|tu lanh|hang xom|cu dan|thue nha|viec nha)\b",
    )),
    ("People, Family & Relationships", (
        r"\b(?:people|person|human|family|parent|mother|father|grandmother|grandfather|grandparent|brother|sister|sibling|son|daughter|child|children|kid|cousin|relative|friend|friendship|partner|couple|husband|wife|marriage|married|relationship|colleague|neighbou?r|acquaintance|community|generation|citizen|population|social)\b",
        r"\b(?:con nguoi|gia dinh|cha me|me|bo|ong|ba|anh trai|chi gai|anh chi em|con trai|con gai|tre em|ho hang|ban be|vo|chong|ket hon|moi quan he|dong nghiep|hang xom|nguoi quen|cong dong|the he|dan so)\b",
    )),
    ("Health, Body & Medicine", (
        r"\b(?:health|healthy|unhealthy|body|head|face|eye|ear|nose|mouth|lip|tooth|teeth|heart|blood|brain|skin|bone|pain|headache|disease|illness|sick|medical|medicine|doctor|dentist|hospital|patient|treatment|therapy|surgery|injury|recover|recovery|mental|physical|fitness|diet|nutrition|sleep|hygiene|symptom|virus|bacter\w*|immune)\b",
        r"\b(?:suc khoe|co the|dau|mat|tai|mui|mieng|moi|rang|tim|mau|nao|da|xuong|dau dau|benh|thuoc|bac si|nha khoa|benh vien|benh nhan|dieu tri|phau thuat|chan thuong|hoi phuc|the chat|dinh duong|giac ngu|trieu chung|vi rut|vi khuan)\b",
    )),
    ("Food, Drink & Shopping", (
        r"\b(?:food|meal|meat|fruit|vegetable|bread|loaf|burger|onion|grape|rice|cake|cheese|egg|fish|chicken|beef|pork|restaurant|cafe|coffee|tea|drink|water|cook|cooking|delicious|taste|shopping|shop|store|market|supermarket|customer|consumer|buy|sell|sale|price|cost|cash|basket|delivery|product|brand|advertis\w*|commercial)\b",
        r"\b(?:thuc an|bua an|thit|trai cay|rau|banh mi|cu hanh|nho|com|banh|pho mai|trung|ca|nha hang|ca phe|tra|do uong|nuoc|nau an|thom ngon|mua sam|cua hang|cho|sieu thi|khach hang|nguoi tieu dung|mua|ban|gia|tien mat|cai ro|giao hang|san pham|thuong hieu|quang cao)\b",
    )),
    ("Education & Language", (
        r"\b(?:education|school|student|teacher|instructor|class|classroom|course|lesson|exam|test|study|learn|teach|training|university|college|academic|degree|qualification|knowledge|skill|language|english|grammar|vocabulary|word|speak|speech|pronunciation|read|reading|write|writing|book|notebook|library|research|scholar\w*)\b",
        r"\b(?:giao duc|truong hoc|hoc sinh|sinh vien|giao vien|lop hoc|khoa hoc|bai hoc|ky thi|thi|hoc|day|dao tao|dai hoc|bang cap|kien thuc|ky nang|ngon ngu|tieng anh|ngu phap|tu vung|tu|noi|phat am|doc|viet|sach|so tay|thu vien|nghien cuu)\b",
    )),
    ("Work, Business & Money", (
        r"\b(?:work|worker|job|career|profession|professional|occupation|employ\w*|staff|manager|management|office|company|corporate|business|industry|factory|department|project|meeting|interview|salary|wage|income|money|financial|finance|econom\w*|bank|budget|profit|loss|trade|invest\w*|market|entrepreneur|productiv\w*|retire\w*)\b",
        r"\b(?:cong viec|viec lam|su nghiep|nghe nghiep|nhan vien|quan ly|van phong|cong ty|doanh nghiep|cong nghiep|nha may|bo phan|du an|cuoc hop|phong van|luong|thu nhap|tien|tai chinh|kinh te|ngan hang|ngan sach|loi nhuan|thua lo|thuong mai|dau tu|nang suat|nghi huu)\b",
    )),
    ("Technology, Media & Communication", (
        r"\b(?:technology|technical|digital|internet|online|computer|keyboard|screen|software|hardware|device|phone|telephone|mobile|email|attachment|website|network|data|information|media|journalis\w*|newspaper|magazine|television|radio|press|message|communicat\w*|contact|reply|notice|advert|publication|broadcast|photograph|camera)\b",
        r"\b(?:cong nghe|ky thuat|ky thuat so|internet|truc tuyen|may tinh|ban phim|man hinh|phan mem|phan cung|thiet bi|dien thoai|thu dien tu|tap tin dinh kem|trang web|mang|du lieu|thong tin|truyen thong|nha bao|bao|tap chi|truyen hinh|phat thanh|tin nhan|giao tiep|lien lac|tra loi|thong bao|xuat ban|phat song|anh|may anh)\b",
    )),
    ("Nature, Animals & Environment", (
        r"\b(?:nature|natural|environment|environmental|climate|weather|rain|rainy|cloud|cloudy|sun|sunny|wind|storm|river|lake|sea|ocean|mountain|forest|countryside|farm|farmer|plant|tree|flower|animal|bird|lion|parrot|species|wildlife|earth|planet|global|pollut\w*|waste|energy|ecosystem|agricultur\w*|rural|landscape|withering)\b",
        r"\b(?:thien nhien|moi truong|khi hau|thoi tiet|mua|may|mat troi|gio|bao|song|ho|bien|dai duong|nui|rung|nong thon|nong trai|nong dan|cay|hoa|dong vat|chim|su tu|vet|loai|hoang da|trai dat|toan cau|o nhiem|rac thai|nang luong|he sinh thai|nong nghiep|canh quan|kho heo)\b",
    )),
    ("Government, Law & Public Issues", (
        r"\b(?:government|govern|politic\w*|policy|public|state|national|international|law|legal|illegal|court|crime|criminal|police|arrest|prison|judge|justice|burglar|burglary|innocent|guilty|authority|rights?|war|military|security|victim|abduct|violence|protest|election|democra\w*|regulat\w*|society)\b",
        r"\b(?:chinh phu|chinh tri|chinh sach|cong cong|quoc gia|quoc te|luat|toa an|toi pham|canh sat|bat giu|nha tu|tham phan|cong ly|an trom|vo toi|co toi|chinh quyen|quyen|chien tranh|quan doi|an ninh|nan nhan|bat coc|bao luc|bieu tinh|bau cu|dan chu|quy dinh|xa hoi)\b",
    )),
    ("Arts, Culture & Entertainment", (
        r"\b(?:art|artist|culture|cultural|music|song|sing|film|movie|cinema|theatre|opera|literature|novel|story|poem|poetry|paint|painting|design|fashion|dance|festival|party|entertain\w*|performance|perform|creative|tradition|heritage|museum|gallery|masterpiece)\b",
        r"\b(?:nghe thuat|nghe si|van hoa|am nhac|bai hat|hat|phim|dien anh|rap chieu|nha hat|van hoc|tieu thuyet|cau chuyen|tho|hoi hoa|thiet ke|thoi trang|nhay|le hoi|buoi tiec|giai tri|bieu dien|sang tao|truyen thong|di san|bao tang|phong tranh|kiet tac)\b",
    )),
    ("Sports, Hobbies & Leisure", (
        r"\b(?:sport|athletic|football|basketball|tennis|judo|swim|swimming|pool|game|play|player|team|coach|match|competition|exercise|gym|hobby|leisure|weekend|park|camp|camping|club|fun|relax|recreation|adventure)\b",
        r"\b(?:the thao|bong da|bong ro|quan vot|judo|boi|be boi|tro choi|choi|doi|huan luyen vien|tran dau|cuoc thi|tap the duc|phong tap|so thich|giai tri|cuoi tuan|cong vien|cam trai|cau lac bo|vui|thu gian|phieu luu)\b",
    )),
    ("Emotions, Personality & Behaviour", (
        r"\b(?:emotion|feeling|feel|happy|sad|angry|afraid|fear|worry|anxious|stress|surprise|excite|love|hate|like|dislike|attitude|behavio\w*|personality|character|friendly|kind|honest|brave|confident|patient|calm|quiet|polite|rude|innocent|absent-minded|empathetic|ambitious|curious|jealous|generous|selfish|mood)\b",
        r"\b(?:cam xuc|cam thay|vui|buon|tuc gian|so hai|lo lang|cang thang|bat ngo|hao hung|yeu|ghet|thich|khong thich|thai do|hanh vi|tinh cach|than thien|tu te|trung thuc|dung cam|tu tin|kien nhan|binh tinh|yen tinh|lich su|tho lo|vo toi|lo dang|cam thong|tham vong|to mo|ghen ti|hao phong|ich ky|tam trang)\b",
    )),
    ("Science, Ideas & Society", (
        r"\b(?:science|scientific|theory|method|process|system|analysis|evidence|experiment|discover\w*|invent\w*|develop\w*|cause|effect|result|factor|issue|problem|solution|concept|idea|reason|purpose|change|progress|advantage|disadvantage|benefit|risk|impact|trend|future|history|modern|global|significant|phenomenon)\b",
        r"\b(?:khoa hoc|ly thuyet|phuong phap|qua trinh|he thong|phan tich|bang chung|thi nghiem|kham pha|phat minh|phat trien|nguyen nhan|anh huong|ket qua|yeu to|van de|giai phap|khai niem|y tuong|ly do|muc dich|thay doi|tien bo|loi the|bat loi|loi ich|rui ro|xu huong|tuong lai|lich su|hien dai|quan trong|hien tuong)\b",
    )),
)
FALLBACK_TOPIC = "General Communication & Everyday Vocabulary"


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def slugify(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "word"


def normalize_text(value: str) -> str:
    value = value.lower().replace("đ", "d")
    return "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )


def normalize_ipa(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    return value if value.startswith("/") and value.endswith("/") else f"/{value.strip('/')}/"


def infer_pos(definition: str) -> str:
    match = re.match(r"^(adj\.|adjective|adv\.|adverb|noun|verb)\b", definition, re.I)
    return match.group(1).rstrip(".").lower() if match else ""


def classify_topic(word: str, vietnamese: str, definition: str) -> str:
    haystack = normalize_text(f"{word} {vietnamese} {definition}")
    for topic, patterns in TOPIC_RULES:
        if any(re.search(pattern, haystack) for pattern in patterns):
            return topic
    return FALLBACK_TOPIC


def rejected_example(value: str) -> bool:
    text = " ".join(str(value or "").replace("“", '"').replace("”", '"').split())
    return not text or bool(re.search(
        r"^(?:here is an example|the (?:term|word|phrase) .+ "
        r"(?:appeared|was used|came up) in (?:a |the )?discussion about)",
        text, re.I,
    ))


def clean_wiki_example(value: str) -> str:
    text = re.sub(r"'''?", "", value)
    text = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    for _ in range(5):
        if not re.search(r"\{\{[^{}]*\}\}", text):
            break
        text = re.sub(r"\{\{([^{}]*)\}\}", lambda m: next(
            (p for p in reversed(m.group(1).split("|")) if p and "=" not in p), ""
        ), text)
    text = re.split(r"\|(?:translation|footer|lit)=", text, maxsplit=1, flags=re.I)[0]
    return " ".join(text.split()).strip(' "')[:300]


def dictionary_example(word: str) -> tuple[str, str]:
    """Dictionary API first, then dictionary quotations from Wiktionary."""
    headers = {"User-Agent": "Mozilla/5.0 Codex vocabulary importer"}
    try:
        req = Request(
            "https://api.dictionaryapi.dev/api/v2/entries/en/" + quote(word),
            headers=headers,
        )
        with urlopen(req, timeout=6) as response:
            entries = json.loads(response.read().decode("utf-8"))
        for entry in entries if isinstance(entries, list) else []:
            for meaning in entry.get("meanings", []):
                for definition in meaning.get("definitions", []):
                    example = " ".join(str(definition.get("example") or "").split())
                    if example and not rejected_example(example):
                        return example[:300], "dictionary"
    except Exception:
        pass
    try:
        url = ("https://en.wiktionary.org/w/api.php?action=parse&page=" + quote(word)
               + "&prop=wikitext&format=json")
        with urlopen(Request(url, headers=headers), timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
        wiki = str(data.get("parse", {}).get("wikitext", {}).get("*", ""))
        english = re.search(r"(?:^|\n)==English==\s*\n([\s\S]*?)(?=\n==[^=]|$)", wiki)
        if english:
            for raw in re.findall(r"\|passage=([^\n]+)", english.group(1)):
                example = clean_wiki_example(raw)
                if (not rejected_example(example)
                        and re.search(rf"(?<!\w){re.escape(word)}(?!\w)", example, re.I)):
                    return example, "wiktionary"
    except Exception:
        pass
    return "", ""


def local_example_index() -> dict[str, list[tuple[int, str, str, str]]]:
    """Index local JSON in the requested DOL/source priority order."""
    index: dict[str, list[tuple[int, str, str, str]]] = defaultdict(list)
    output_names = {f"dol-gpt-codex-speaking-2026-03-dol-ielts-vocabulary-{c}.json"
                    for _, c, _ in BANDS}
    for path in (ROOT / "data").rglob("*.json"):
        if path.name in output_names:
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        meta = " ".join(str(doc.get(k, "")) for k in
                        ("id", "source", "group", "book", "skill", "title")).lower()
        if re.search(r"(?:cambridge|\bcam\b)", meta) and re.search(r"reading|listening", meta):
            priority, origin = 500, "dol-cambridge"
        elif re.search(r"actual test|practice test plus|test plus|\bptp\b", meta):
            priority, origin = 400, "dol-test"
        elif "dol" in meta or "dol" in str(path).lower():
            priority, origin = 300, "dol-other"
        else:
            priority, origin = 200, "local-source"
        for item in doc.get("items", []):
            if not isinstance(item, dict):
                continue
            word = normalize_text(str(item.get("text") or item.get("word") or "")).strip()
            example = str(item.get("example") or item.get("exEn") or "").strip()
            example = re.sub(r"^(?:ex(?:ample)?|e\.g\.)\s*:\s*", "", example, flags=re.I)
            example_vi = str(item.get("exampleVi") or item.get("exVi") or "").strip()
            if word and example and not rejected_example(example):
                index[word].append((priority, example, example_vi, origin))
    for rows in index.values():
        rows.sort(key=lambda row: row[0], reverse=True)
    return index


def generated_example(word: str, vietnamese: str, topic: str, pos: str) -> tuple[str, str]:
    """Last-resort genuine usage, never a sentence describing the term itself."""
    if pos in {"adj", "adjective"}:
        return (f"The committee considered the proposal {word}.",
                f"Ủy ban cho rằng đề xuất này {vietnamese.lower()}.")
    if pos in {"adv", "adverb"} or word.lower().endswith("ly"):
        return (f"The committee responded {word} to the proposal.",
                f"Ủy ban đã phản hồi {vietnamese.lower()} đối với đề xuất.")
    if pos == "verb":
        return (f"Community leaders decided to {word} after discussing the issue carefully.",
                f"Các lãnh đạo cộng đồng quyết định {vietnamese.lower()} sau khi thảo luận kỹ vấn đề.")
    return (f"The report examines {word} and its effect on the local community.",
            f"Báo cáo xem xét {vietnamese.lower()} và tác động của nó đối với cộng đồng địa phương.")


def card_html(item: dict[str, object]) -> str:
    definition = str(item.get("definition") or "")
    definition_html = (
        f'<p class="en definition">{escape(definition)}</p>' if definition else ""
    )
    return (
        '<div class="vocab dol-card">'
        f'<div class="head">{escape(str(item["text"]))} '
        f'<span class="ipa">{escape(str(item["ipaUK"]))}</span></div>'
        f'<p class="vi main-meaning">{escape(str(item["vn"]))}</p>'
        f"{definition_html}"
        f'<p class="en ex">{escape(str(item["example"]))}</p>'
        f'<p class="vi ex-vi">{escape(str(item["exampleVi"]))}</p></div>'
    )


def source_section() -> dict[str, object]:
    return {
        "id": "sources",
        "title": "Sources",
        "level": 1,
        "wordCount": 0,
        "html": (
            '<p class="en">Vocabulary, IPA, Vietnamese meanings, and available English '
            f'definitions extracted from <a class="ext-link" href="{SOURCE_URL}" '
            'target="_blank" rel="noopener">DOL English</a> for personal IELTS study. '
            "Topic labels were added for easier study.</p>"
            '<p class="vi">Từ vựng được trích từ DOL English; nhãn chủ đề được '
            'bổ sung để học thuận tiện hơn.</p>'
        ),
    }


def main() -> None:
    request = Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        source_html = response.read().decode("utf-8")

    parser = TableParser()
    parser.feed(source_html)
    if len(parser.tables) != 4:
        raise RuntimeError(f"Expected 4 vocabulary tables, found {len(parser.tables)}")

    local_examples = local_example_index()
    all_words = [row[0] for table in parser.tables for row in table[1:] if len(row) >= 3 and row[0]]
    dictionary_examples: dict[str, tuple[str, str]] = {}
    with ThreadPoolExecutor(max_workers=32) as pool:
        futures = {pool.submit(dictionary_example, word): word for word in all_words}
        for count, future in enumerate(as_completed(futures), start=1):
            word = futures[future]
            try:
                dictionary_examples[normalize_text(word)] = future.result()
            except Exception:
                dictionary_examples[normalize_text(word)] = ("", "")
            if count % 100 == 0:
                print(f"Resolved dictionary examples: {count}/{len(futures)}")

    now = datetime.now().astimezone()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_paths: list[Path] = []

    for band_num, ((band, cefr, band_score), table) in enumerate(
        zip(BANDS, parser.tables), start=1
    ):
        items: list[dict[str, object]] = []
        by_topic: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row_num, row in enumerate(table[1:], start=1):
            if len(row) < 3 or not row[0]:
                continue
            word, ipa, vietnamese = row[:3]
            definition = row[3] if len(row) > 3 else ""
            topic = classify_topic(word, vietnamese, definition)
            pos = infer_pos(definition)
            example, origin = dictionary_examples.get(normalize_text(word), ("", ""))
            example_vi = ""
            if not example:
                local = local_examples.get(normalize_text(word), [])
                if local:
                    _, example, example_vi, origin = local[0]
            if not example:
                example, example_vi = generated_example(word, vietnamese, topic, pos)
                origin = "generated"
            item: dict[str, object] = {
                "id": f"{cefr}-{row_num:03d}-{slugify(word)}",
                "passageLabel": topic,
                "passageName": topic,
                "passageNum": 0,
                "text": word,
                "pos": pos,
                "vn": vietnamese,
                "ipaUK": normalize_ipa(ipa),
                "definition": definition,
                "example": example,
                "exampleVi": example_vi,
                "exampleIpa": "",
                "exampleOrigin": origin,
                "l1": "Others",
                "l2": "Speaking 2026",
                "l3": band,
                "l4": topic,
            }
            items.append(item)
            by_topic[topic].append(item)

        topic_order = [topic for topic, _ in TOPIC_RULES] + [FALLBACK_TOPIC]
        populated_topics = [topic for topic in topic_order if by_topic.get(topic)]
        for topic_num, topic in enumerate(populated_topics, start=1):
            for item in by_topic[topic]:
                item["passageNum"] = topic_num

        sections = [
            {
                "id": f"topic-{topic_num:02d}-{slugify(topic)}",
                "title": topic,
                "level": 1,
                "wordCount": len(by_topic[topic]),
                "html": "\n".join(card_html(item) for item in by_topic[topic]),
            }
            for topic_num, topic in enumerate(populated_topics, start=1)
        ]
        sections.append(source_section())

        lesson_id = f"dol-gpt-codex-speaking-2026-03-dol-ielts-vocabulary-{cefr}"
        document = {
            "schema": 2,
            "format": "dol-vocab",
            "id": lesson_id,
            "type": "vocab",
            "source": "codex",
            "category": "dol-vocab",
            "topicNumber": 0,
            "title": f"DOL IELTS Vocabulary · {band}",
            "group": "Others",
            "book": "Speaking 2026",
            "bookNum": 2026,
            "testNum": band_score,
            "skill": "speaking",
            "superlmsFlat": True,
            "l1": "Others",
            "l2": "Speaking 2026",
            "l3": band,
            "url": SOURCE_URL,
            "dateTime": now.strftime("%Y-%m-%dT%H:%M"),
            "contentUpdatedAt": now.isoformat(timespec="seconds"),
            "wordCount": len(items),
            "words": [str(item["text"]) for item in items],
            "items": items,
            "sections": sections,
        }
        output = OUTPUT_DIR / f"{lesson_id}.json"
        output.write_text(
            json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        generated_paths.append(output)
        counts = ", ".join(f"{topic}: {len(by_topic[topic])}" for topic in populated_topics)
        print(f"Wrote {len(items)} entries to {output.name}")
        print(f"  {counts}")

    # The combined file is obsolete once all four replacements exist.
    if len(generated_paths) == 4 and all(path.is_file() for path in generated_paths):
        OLD_COMBINED_OUTPUT.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
