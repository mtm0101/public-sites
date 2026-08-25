#!/usr/bin/env python3
"""Generate and validate the initial immutable Study App test question bank.

The published IDs in pack-0001 are stable. Future generators must add a new
pack instead of renumbering or reusing an existing question ID.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEST_ROOT = ROOT / "data" / "chatgpt" / "tests"
PACK_PATH = TEST_ROOT / "question-bank" / "toeic" / "grammar" / "pack-0001.json"
DEFINITION_PATH = TEST_ROOT / "definitions" / "toeic-grammar-advanced-001.json"
TAXONOMY_PATH = TEST_ROOT / "taxonomy.json"
MANIFEST_PATH = TEST_ROOT / "manifest.json"
STATS_PATH = TEST_ROOT / "bank-stats.json"
GENERATED_AT = "2026-08-25T00:00:00Z"


CATEGORIES = [
    ("grammar.word-forms", "Word forms", "Từ loại"),
    ("grammar.subject-verb-agreement", "Subject–verb agreement", "Sự hòa hợp chủ ngữ–động từ"),
    ("grammar.verb-tense", "Verb tense", "Thì của động từ"),
    ("grammar.verb-aspect", "Verb aspect and sequence", "Thể và trình tự thời gian"),
    ("grammar.passive-causative", "Passive voice and causatives", "Câu bị động và cấu trúc nhờ khiến"),
    ("grammar.gerund-infinitive", "Gerunds and infinitives", "Danh động từ và động từ nguyên mẫu"),
    ("grammar.modals", "Modal verbs", "Động từ khuyết thiếu"),
    ("grammar.conditionals", "Conditionals", "Câu điều kiện"),
    ("grammar.subjunctive", "Mandative subjunctive", "Thức giả định sau yêu cầu/đề nghị"),
    ("grammar.relative-clauses", "Relative clauses", "Mệnh đề quan hệ"),
    ("grammar.reduced-clauses", "Reduced relative clauses", "Mệnh đề quan hệ rút gọn"),
    ("grammar.participles", "Participial clauses", "Mệnh đề phân từ"),
    ("grammar.noun-clauses", "Noun clauses", "Mệnh đề danh từ"),
    ("grammar.adverbial-clauses", "Adverbial clauses", "Mệnh đề trạng ngữ"),
    ("grammar.connectors", "Conjunctions and prepositions", "Liên từ và giới từ"),
    ("grammar.articles-countability", "Articles and countability", "Mạo từ và danh từ đếm được"),
    ("grammar.determiners-quantifiers", "Determiners, pronouns, and quantifiers", "Từ hạn định, đại từ và lượng từ"),
    ("grammar.comparison", "Comparison and degree", "So sánh và mức độ"),
    ("grammar.parallelism", "Parallel structures", "Cấu trúc song song"),
    ("grammar.prepositions-collocations", "Prepositions and business collocations", "Giới từ và kết hợp từ thương mại"),
]


SCENARIOS = [
    ("finance team", "nhóm tài chính", "quarterly forecast", "dự báo quý"),
    ("procurement department", "phòng thu mua", "supplier agreement", "hợp đồng nhà cung cấp"),
    ("operations committee", "ủy ban vận hành", "warehouse plan", "kế hoạch kho hàng"),
    ("marketing division", "bộ phận tiếp thị", "product campaign", "chiến dịch sản phẩm"),
    ("human resources unit", "bộ phận nhân sự", "training policy", "chính sách đào tạo"),
    ("quality assurance group", "nhóm bảo đảm chất lượng", "inspection report", "báo cáo kiểm tra"),
    ("regional sales office", "văn phòng kinh doanh khu vực", "client proposal", "đề xuất khách hàng"),
    ("legal affairs team", "nhóm pháp chế", "compliance review", "đợt rà soát tuân thủ"),
    ("customer support center", "trung tâm hỗ trợ khách hàng", "service procedure", "quy trình dịch vụ"),
    ("logistics department", "phòng hậu cần", "delivery schedule", "lịch giao hàng"),
]


def study(en: str, vi: str) -> dict:
    return {"en": en, "vi": vi}


def normalized_fingerprint(stem: str, options: list[str]) -> str:
    text = "|".join([stem, *options]).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_question(
    category_index: int,
    item_index: int,
    stem: str,
    stem_vi: str,
    candidates: list[dict],
    correct_source_index: int,
    rule_en: str,
    rule_vi: str,
    cefr: str,
    difficulty: int,
    workplace_topic: str,
) -> dict:
    category_id, category_en, category_vi = CATEGORIES[category_index]
    desired_correct = (category_index + item_index) % 4
    correct_candidate = candidates[correct_source_index]
    wrong_candidates = [c for i, c in enumerate(candidates) if i != correct_source_index]
    ordered = wrong_candidates[:]
    ordered.insert(desired_correct, correct_candidate)
    qid = f"toeic-g-{category_id.split('.')[-1]}-{item_index + 1:03d}"
    options = []
    correct_option_id = ""
    for option_index, candidate in enumerate(ordered):
        option_id = chr(65 + option_index)
        is_correct = candidate is correct_candidate
        if is_correct:
            correct_option_id = option_id
            explanation_en = f"“{candidate['en']}” is correct. {rule_en}"
            explanation_vi = f"“{candidate['en']}” là đáp án đúng. {rule_vi}"
        else:
            explanation_en = (
                f"“{candidate['en']}” is not correct here. {candidate['why_en']} "
                f"In this sentence, {rule_en[0].lower() + rule_en[1:]}"
            )
            explanation_vi = (
                f"“{candidate['en']}” không đúng trong câu này. {candidate['why_vi']} "
                f"Trong câu này, {rule_vi[0].lower() + rule_vi[1:]}"
            )
        options.append({
            "id": option_id,
            "text": study(candidate["en"], candidate["vi"]),
            "correct": is_correct,
            "explanation": study(explanation_en, explanation_vi),
        })
    return {
        "id": qid,
        "version": 1,
        "status": "published",
        "type": "single-choice",
        "examFamily": "toeic-lr",
        "examPart": "reading-part-5",
        "primaryCategoryId": category_id,
        "secondaryCategoryIds": [],
        "categoryLabel": study(category_en, category_vi),
        "cefr": cefr,
        "difficulty": difficulty,
        "targetToeicRange": {"min": 700, "max": 990},
        "workplaceTopic": workplace_topic,
        "prompt": study(stem, stem_vi),
        "options": options,
        "correctOptionId": correct_option_id,
        "explanation": {
            "rule": study(rule_en, rule_vi),
            "summary": study(
                f"The best answer is {correct_option_id}, “{correct_candidate['en']}”. The blank tests {category_en.lower()} in a workplace context.",
                f"Đáp án tốt nhất là {correct_option_id}, “{correct_candidate['en']}”. Chỗ trống kiểm tra {category_vi.lower()} trong bối cảnh công việc.",
            ),
        },
        "fingerprint": normalized_fingerprint(stem, [o["text"]["en"] for o in options]),
        "contentUpdatedAt": GENERATED_AT,
    }


def cand(en: str, vi: str, why_en: str, why_vi: str) -> dict:
    return {"en": en, "vi": vi, "why_en": why_en, "why_vi": why_vi}


def category_questions(category_index: int) -> list[dict]:
    questions = []
    for i, (team, team_vi, obj, obj_vi) in enumerate(SCENARIOS):
        cefr = "B2" if i < 5 else "C1"
        difficulty = 3 if i < 4 else 4 if i < 8 else 5
        topic = ["finance", "procurement", "operations", "marketing", "human-resources", "quality", "sales", "legal", "customer-service", "logistics"][i]

        if category_index == 0:
            forms = [
                ("accuracy", "accurate", "accurately", "accurate", "chính xác"),
                ("reliability", "reliable", "reliably", "reliable", "đáng tin cậy"),
                ("efficiency", "efficient", "efficiently", "efficient", "hiệu quả"),
                ("strategy", "strategic", "strategically", "strategic", "mang tính chiến lược"),
                ("consistency", "consistent", "consistently", "consistent", "nhất quán"),
                ("comprehension", "comprehensive", "comprehensively", "comprehensive", "toàn diện"),
                ("precision", "precise", "precisely", "precise", "chính xác"),
                ("substance", "substantial", "substantially", "substantial", "đáng kể"),
                ("persuasion", "persuasive", "persuasively", "persuasive", "thuyết phục"),
                ("caution", "cautious", "cautiously", "cautious", "thận trọng"),
            ][i]
            noun, adjective, adverb, correct, gloss = forms
            noun_plural = {
                "accuracy": "accuracies", "reliability": "reliabilities", "efficiency": "efficiencies",
                "strategy": "strategies", "consistency": "consistencies", "comprehension": "comprehensions",
                "precision": "precisions", "substance": "substances", "persuasion": "persuasions",
                "caution": "cautions",
            }[noun]
            stem = f"The {team} submitted a remarkably ______ assessment of the {obj}."
            stem_vi = f"{team_vi.capitalize()} đã nộp một bản đánh giá ______ đáng chú ý về {obj_vi}."
            candidates = [
                cand(noun, gloss + " (danh từ)", "It is a noun, but the blank modifies the noun “assessment” and therefore requires an adjective.", "Đây là danh từ, nhưng chỗ trống bổ nghĩa cho “assessment” nên cần tính từ."),
                cand(adjective, gloss + " (tính từ)", "It is the adjective form required before the noun “assessment”.", "Đây là dạng tính từ cần đứng trước danh từ “assessment”."),
                cand(adverb, "một cách " + gloss + " (trạng từ)", "It is an adverb and cannot directly modify the noun “assessment” in this position.", "Đây là trạng từ và không thể trực tiếp bổ nghĩa cho danh từ “assessment” ở vị trí này."),
                cand(noun_plural, gloss + " (dạng số nhiều không phù hợp)", "This plural noun form does not function as the required adjective.", "Dạng danh từ số nhiều này không thể làm tính từ cần thiết."),
            ]
            rule_en = "An adjective is required after the degree adverb “remarkably” and before the noun “assessment”."
            rule_vi = "Cần một tính từ sau trạng từ chỉ mức độ “remarkably” và trước danh từ “assessment”."
            correct_index = 1

        elif category_index == 1:
            plural = i % 2 == 0
            if plural:
                stem = f"Neither the revised timeline nor the cost estimates for the {obj} ______ available to the {team}."
                stem_vi = f"Cả tiến độ sửa đổi lẫn các ước tính chi phí cho {obj_vi} đều chưa ______ cho {team_vi}."
                correct, subject = "are", "the nearer subject “cost estimates” is plural"
                subject_vi = "chủ ngữ gần động từ hơn là “cost estimates” ở số nhiều"
            else:
                stem = f"Each of the recommendations in the {obj} ______ approval from the {team}."
                stem_vi = f"Mỗi khuyến nghị trong {obj_vi} ______ sự phê duyệt của {team_vi}."
                correct, subject = "requires", "the head subject “Each” is singular"
                subject_vi = "chủ ngữ chính “Each” ở số ít"
            candidates = [
                cand("is" if plural else "require", "dạng không hòa hợp", "This verb does not agree in number with the controlling subject.", "Động từ này không hòa hợp về số với chủ ngữ chi phối."),
                cand(correct, "dạng động từ hòa hợp chính xác", "This verb agrees with the controlling subject.", "Động từ này hòa hợp chính xác với chủ ngữ chi phối."),
                cand("have" if plural else "are requiring", "dạng động từ không phù hợp", "Its form or auxiliary pattern does not match the sentence structure.", "Dạng hoặc cấu trúc trợ động từ không phù hợp với câu."),
                cand("be", "động từ nguyên mẫu", "A bare infinitive cannot serve as the finite verb here.", "Động từ nguyên mẫu không thể làm động từ hữu hạn ở đây."),
            ]
            rule_en = f"The finite verb must agree with the controlling subject; {subject}."
            rule_vi = f"Động từ hữu hạn phải hòa hợp với chủ ngữ chi phối; {subject_vi}."
            correct_index = 1

        elif category_index == 2:
            verbs = [
                ("decrease", "decreased", "has decreased", "had decreased", "giảm"),
                ("improve", "improved", "has improved", "had improved", "cải thiện"),
                ("expand", "expanded", "has expanded", "had expanded", "mở rộng"),
                ("stabilize", "stabilized", "has stabilized", "had stabilized", "ổn định"),
                ("increase", "increased", "has increased", "had increased", "tăng"),
                ("decline", "declined", "has declined", "had declined", "suy giảm"),
                ("accelerate", "accelerated", "has accelerated", "had accelerated", "tăng tốc"),
                ("recover", "recovered", "has recovered", "had recovered", "phục hồi"),
                ("strengthen", "strengthened", "has strengthened", "had strengthened", "tăng cường"),
                ("grow", "grew", "has grown", "had grown", "tăng trưởng"),
            ][i]
            base, past, perfect, past_perfect, gloss = verbs
            stem = f"Since the {team} introduced the new {obj} in January, overall performance ______ significantly."
            stem_vi = f"Kể từ khi {team_vi} triển khai {obj_vi} mới vào tháng Một, hiệu suất tổng thể đã ______ đáng kể."
            candidates = [
                cand(base, gloss + " (hiện tại đơn)", "The simple present does not express a change continuing from January to the present.", "Hiện tại đơn không diễn tả thay đổi kéo dài từ tháng Một đến hiện tại."),
                cand(past, "đã " + gloss + " (quá khứ đơn)", "The simple past conflicts with “Since ... in January,” which connects past initiation to the present.", "Quá khứ đơn xung đột với “Since ... in January”, cụm nối thời điểm bắt đầu trong quá khứ với hiện tại."),
                cand(perfect, "đã " + gloss + " (hiện tại hoàn thành)", "The present perfect correctly connects the January change with the present result.", "Hiện tại hoàn thành nối chính xác thay đổi từ tháng Một với kết quả hiện tại."),
                cand(past_perfect, "đã " + gloss + " (quá khứ hoàn thành)", "The past perfect requires another past reference point, which is absent here.", "Quá khứ hoàn thành cần một mốc quá khứ khác, nhưng câu này không có."),
            ]
            rule_en = "The present perfect is required with “since” for a development that began in the past and remains relevant now."
            rule_vi = "Cần hiện tại hoàn thành với “since” cho diễn biến bắt đầu trong quá khứ và vẫn liên quan đến hiện tại."
            correct_index = 2

        elif category_index == 3:
            actions = [
                ("complete", "completed", "had completed", "has completed", "hoàn tất", "every section of"),
                ("review", "reviewed", "had reviewed", "has reviewed", "rà soát", "the final terms of"),
                ("approve", "approved", "had approved", "has approved", "phê duyệt", "the proposed layout for"),
                ("finalize", "finalized", "had finalized", "has finalized", "hoàn thiện", "the wording of"),
                ("verify", "verified", "had verified", "has verified", "xác minh", "all details in"),
                ("negotiate", "negotiated", "had negotiated", "has negotiated", "đàm phán", "the key terms of"),
                ("test", "tested", "had tested", "has tested", "kiểm thử", "the assumptions behind"),
                ("revise", "revised", "had revised", "has revised", "sửa đổi", "the appendices to"),
                ("calculate", "calculated", "had calculated", "has calculated", "tính toán", "the projected costs in"),
                ("document", "documented", "had documented", "has documented", "lập hồ sơ", "all changes to"),
            ][i]
            base, past, past_perfect, present_perfect, gloss, complement = actions
            stem = f"By the time the external reviewers arrived, the {team} ______ {complement} the {obj}."
            stem_vi = f"Trước khi các chuyên gia đánh giá bên ngoài đến, {team_vi} đã ______ mọi phần của {obj_vi}."
            candidates = [
                cand(base, gloss + " (nguyên mẫu)", "The bare form cannot express the earlier completed past action.", "Dạng nguyên mẫu không thể diễn tả hành động quá khứ hoàn tất trước đó."),
                cand(past, "đã " + gloss + " (quá khứ đơn)", "The simple past does not make the sequence between the two past events explicit.", "Quá khứ đơn không làm rõ trình tự giữa hai sự kiện quá khứ."),
                cand(past_perfect, "đã " + gloss + " (quá khứ hoàn thành)", "The past perfect marks completion before the reviewers arrived.", "Quá khứ hoàn thành đánh dấu việc hoàn tất trước khi các chuyên gia đến."),
                cand(present_perfect, "đã " + gloss + " (hiện tại hoàn thành)", "The present perfect cannot be anchored before the completed past event “arrived”.", "Hiện tại hoàn thành không thể được neo trước sự kiện quá khứ đã hoàn tất “arrived”."),
            ]
            rule_en = "The past perfect identifies the action completed before another finished past event introduced by “By the time”."
            rule_vi = "Quá khứ hoàn thành xác định hành động hoàn tất trước một sự kiện quá khứ khác với “By the time”."
            correct_index = 2

        elif category_index == 4:
            actions = ["inspect", "approve", "review", "translate", "verify", "sign", "secure", "archive", "update", "certify"]
            action = actions[i]
            participle = {
                "inspect": "inspected", "approve": "approved", "review": "reviewed",
                "translate": "translated", "verify": "verified", "replace": "replaced",
                "sign": "signed", "secure": "secured", "archive": "archived", "update": "updated", "certify": "certified",
            }[action]
            stem = f"All documents connected with the {obj} must ______ by an independent specialist before release."
            stem_vi = f"Mọi tài liệu liên quan đến {obj_vi} phải được ______ bởi một chuyên gia độc lập trước khi phát hành."
            candidates = [
                cand(action, action + " (chủ động)", "After “must,” this active form would make “documents” perform the action.", "Sau “must”, dạng chủ động này khiến “documents” trở thành bên thực hiện hành động."),
                cand(f"be {participle}", "được xử lý (bị động)", "“Must + be + past participle” correctly forms the passive modal construction.", "“Must + be + quá khứ phân từ” tạo đúng cấu trúc khuyết thiếu bị động."),
                cand(f"have {participle}", "đã xử lý (chủ động hoàn thành)", "This perfect active construction does not give “documents” the required passive role.", "Cấu trúc hoàn thành chủ động này không tạo vai trò bị động cần thiết cho “documents”."),
                cand(f"being {participle}", "đang được xử lý", "A gerund-participial form cannot directly follow the modal “must”.", "Dạng danh động từ/phân từ không thể trực tiếp theo sau “must”."),
            ]
            rule_en = "Because the documents receive the action, the modal must be followed by the passive form “be + past participle”."
            rule_vi = "Vì tài liệu nhận hành động, động từ khuyết thiếu phải đi với dạng bị động “be + quá khứ phân từ”."
            correct_index = 1

        elif category_index == 5:
            verbs = [
                ("postponed", "making", "to make", "make", "made", "the forecast public until the supporting data could be verified"),
                ("considered", "revising", "to revise", "revise", "revised", "the supplier agreement after receiving legal advice"),
                ("recommended", "updating", "to update", "update", "updated", "the warehouse plan before the next inspection"),
                ("avoided", "disclosing", "to disclose", "disclose", "disclosed", "the campaign details before the official launch"),
                ("finished", "reviewing", "to review", "review", "reviewed", "the training policy before Friday's meeting"),
                ("discussed", "extending", "to extend", "extend", "extended", "the inspection period by two weeks"),
                ("suggested", "reducing", "to reduce", "reduce", "reduced", "the proposal's scope to control costs"),
                ("delayed", "announcing", "to announce", "announce", "announced", "the review findings until the evidence was complete"),
                ("practiced", "presenting", "to present", "present", "presented", "the new procedure before the client workshop"),
                ("risked", "losing", "to lose", "lose", "lost", "the reserved delivery slot by changing the order"),
            ][i]
            trigger, gerund, infinitive, bare, participle, complement = verbs
            stem = f"The {team} {trigger} ______ {complement}."
            stem_vi = f"{team_vi.capitalize()} đã dùng cấu trúc sau “{trigger}” để diễn tả việc ______ trong tình huống công việc này."
            candidates = [
                cand(gerund, "dạng V-ing phù hợp", f"The verb “{trigger}” is followed by a gerund in this meaning.", f"Động từ “{trigger}” đi với danh động từ trong nghĩa này."),
                cand(infinitive, "động từ nguyên mẫu có to", f"“{trigger}” does not take a to-infinitive in this construction.", f"“{trigger}” không đi với động từ nguyên mẫu có “to” trong cấu trúc này."),
                cand(bare, "động từ nguyên mẫu không to", "A bare infinitive cannot complement this verb.", "Động từ nguyên mẫu không “to” không thể bổ nghĩa cho động từ này."),
                cand(participle, "quá khứ phân từ", "A past participle does not provide the required object activity.", "Quá khứ phân từ không thể hiện hoạt động làm tân ngữ cần thiết."),
            ]
            rule_en = f"The verb “{trigger}” requires a gerund complement to name the activity under discussion."
            rule_vi = f"Động từ “{trigger}” cần bổ ngữ dạng danh động từ để gọi tên hoạt động đang được nói đến."
            correct_index = 0

        elif category_index == 6:
            stem = f"The {team} ______ have checked the figures in the {obj} more carefully; the discrepancy was clearly visible."
            stem_vi = f"{team_vi.capitalize()} ______ đã kiểm tra các số liệu trong {obj_vi} cẩn thận hơn; sai lệch rất dễ nhận thấy."
            candidates = [
                cand("should", "lẽ ra nên", "“Should have + past participle” expresses criticism of an unfulfilled past duty.", "“Should have + quá khứ phân từ” diễn tả lời phê bình về nghĩa vụ quá khứ không được thực hiện."),
                cand("must", "chắc hẳn", "“Must have” expresses a strong deduction, not criticism about what was advisable.", "“Must have” diễn tả suy đoán mạnh, không phải lời phê bình về điều nên làm."),
                cand("can", "có thể", "“Can have checked” is not the normal form for this past criticism.", "“Can have checked” không phải dạng thông thường cho lời phê bình quá khứ này."),
                cand("will", "sẽ", "“Will have checked” normally marks future completion or confident prediction, not past regret.", "“Will have checked” thường chỉ hoàn tất trong tương lai hoặc dự đoán chắc chắn, không phải hối tiếc quá khứ."),
            ]
            rule_en = "“Should have + past participle” is used for an action that was advisable in the past but did not happen."
            rule_vi = "“Should have + quá khứ phân từ” dùng cho hành động đáng lẽ nên làm trong quá khứ nhưng đã không xảy ra."
            correct_index = 0

        elif category_index == 7:
            stem = f"If the {team} had identified the defect earlier, it ______ an alternative {obj} before the deadline."
            stem_vi = f"Nếu {team_vi} phát hiện lỗi sớm hơn, bộ phận đó ______ một {obj_vi} thay thế trước hạn chót."
            candidates = [
                cand("would arrange", "sẽ sắp xếp", "This is a present/future conditional result and does not match the unreal past condition.", "Đây là kết quả điều kiện hiện tại/tương lai và không khớp với điều kiện quá khứ không có thật."),
                cand("would have arranged", "đã có thể sắp xếp", "This is the correct result form for an unreal past condition.", "Đây là dạng kết quả đúng cho điều kiện quá khứ không có thật."),
                cand("will have arranged", "sẽ đã sắp xếp", "The future perfect is incompatible with the counterfactual “had identified”.", "Tương lai hoàn thành không phù hợp với điều kiện trái thực tế “had identified”."),
                cand("had arranged", "đã sắp xếp", "A past perfect result clause omits the required modal consequence.", "Mệnh đề kết quả quá khứ hoàn thành thiếu hệ quả khuyết thiếu cần thiết."),
            ]
            rule_en = "A third conditional uses “if + past perfect” and “would have + past participle” for an unreal past result."
            rule_vi = "Câu điều kiện loại ba dùng “if + quá khứ hoàn thành” và “would have + quá khứ phân từ” cho kết quả quá khứ không có thật."
            correct_index = 1

        elif category_index == 8:
            verbs = [("adopt", "the new reporting procedure"), ("revise", "the supplier agreement"), ("submit", "the warehouse plan"), ("retain", "the marketing agency"), ("appoint", "a training coordinator"), ("follow", "the inspection protocol"), ("disclose", "the proposal terms"), ("record", "the review findings"), ("inspect", "the service equipment"), ("provide", "a revised delivery estimate")]
            verb, complement = verbs[i]
            past = {"submit": "submitted"}.get(verb, verb + "d" if verb.endswith("e") else verb + "ed")
            stem = f"The executive committee recommended that the {team} ______ {complement} immediately."
            stem_vi = f"Ban điều hành đề nghị {team_vi} ______ hạng mục cần thiết ngay lập tức."
            candidates = [
                cand(verb, verb + " (nguyên mẫu)", "The base form is required in a mandative that-clause after “recommended”.", "Dạng nguyên mẫu được yêu cầu trong mệnh đề giả định sau “recommended”."),
                cand(verb + "s", verb + " (ngôi thứ ba số ít)", "The third-person ending is not used in the mandative subjunctive.", "Đuôi ngôi thứ ba không được dùng trong thức giả định mang nghĩa yêu cầu."),
                cand("to " + verb, "to + động từ", "The that-clause requires a finite base form, not a to-infinitive.", "Mệnh đề “that” cần dạng nguyên mẫu hữu hạn, không phải động từ nguyên mẫu có “to”."),
                cand(past, "quá khứ", "Past tense would incorrectly present the recommended action as an earlier fact.", "Quá khứ sẽ trình bày sai hành động được đề nghị như một sự việc đã xảy ra."),
            ]
            rule_en = "After a recommendation followed by a that-clause, formal English uses the mandative subjunctive base verb."
            rule_vi = "Sau một lời đề nghị kèm mệnh đề “that”, tiếng Anh trang trọng dùng động từ nguyên mẫu của thức giả định."
            correct_index = 0

        elif category_index == 9:
            stem = f"The consultant ______ analysis helped the {team} improve the {obj} will return next month."
            stem_vi = f"Chuyên gia tư vấn ______ phân tích đã giúp {team_vi} cải thiện {obj_vi} sẽ trở lại vào tháng tới."
            candidates = [
                cand("who", "người mà", "“Who” is a subject or object relative pronoun; it cannot directly show possession before “analysis”.", "“Who” là đại từ quan hệ làm chủ ngữ hoặc tân ngữ; không thể trực tiếp chỉ sở hữu trước “analysis”."),
                cand("whom", "người mà (tân ngữ)", "“Whom” marks an object and cannot function as the possessive determiner of “analysis”.", "“Whom” chỉ tân ngữ và không thể làm từ hạn định sở hữu cho “analysis”."),
                cand("whose", "có ... của người đó", "“Whose” correctly marks that the analysis belongs to the consultant.", "“Whose” chỉ chính xác rằng bản phân tích thuộc về chuyên gia tư vấn."),
                cand("which", "cái mà", "“Which” does not express the required personal possession in this structure.", "“Which” không diễn tả sở hữu của người cần có trong cấu trúc này."),
            ]
            rule_en = "The possessive relative determiner “whose” must precede the owned noun “analysis”."
            rule_vi = "Từ hạn định quan hệ sở hữu “whose” phải đứng trước danh từ được sở hữu “analysis”."
            correct_index = 2

        elif category_index == 10:
            stem = f"Applications ______ after the {team} completes its review of the {obj} will be considered in the next cycle."
            stem_vi = f"Các hồ sơ ______ sau khi {team_vi} hoàn tất việc rà soát {obj_vi} sẽ được xem xét trong đợt tiếp theo."
            candidates = [
                cand("receiving", "đang nhận", "The active participle would mean that the applications receive something themselves.", "Phân từ chủ động sẽ có nghĩa các hồ sơ tự nhận một thứ gì đó."),
                cand("received", "được nhận", "The past participle correctly reduces “applications that are received”.", "Quá khứ phân từ rút gọn chính xác “applications that are received”."),
                cand("receive", "nhận", "A bare finite-looking verb cannot modify “Applications” without a relative subject.", "Động từ dạng nguyên mẫu không thể bổ nghĩa cho “Applications” nếu thiếu chủ ngữ quan hệ."),
                cand("were received", "đã được nhận", "A finite passive clause requires a relative pronoun such as “that”.", "Mệnh đề bị động hữu hạn cần đại từ quan hệ như “that”."),
            ]
            rule_en = "A passive relative clause can be reduced to a past-participial phrase: “applications received ...”."
            rule_vi = "Mệnh đề quan hệ bị động có thể rút gọn thành cụm quá khứ phân từ: “applications received ...”."
            correct_index = 1

        elif category_index == 11:
            emotions = [
                ("Encouraged", "Khích lệ"), ("Concerned", "Lo ngại"), ("Impressed", "Ấn tượng"),
                ("Motivated", "Được thúc đẩy"), ("Surprised", "Ngạc nhiên"), ("Alarmed", "Báo động"),
                ("Reassured", "Yên tâm"), ("Frustrated", "Thất vọng"), ("Inspired", "Truyền cảm hứng"),
                ("Convinced", "Bị thuyết phục"),
            ]
            correct, correct_vi = emotions[i]
            stem = f"______ by the latest results, the {team} revised its next steps for the {obj}."
            stem_vi = f"______ bởi các kết quả mới nhất, {team_vi} đã điều chỉnh các bước tiếp theo cho {obj_vi}."
            candidates = [
                cand(correct, correct_vi, "The past participle shows how the team was affected by the results.", "Quá khứ phân từ cho thấy nhóm bị tác động như thế nào bởi kết quả."),
                cand(correct[:-2] + "ing" if correct.endswith("ed") else correct + "ing", "dạng -ing", "The -ing form would make the team cause this feeling rather than experience it.", "Dạng -ing sẽ khiến nhóm gây ra cảm xúc thay vì trải nghiệm cảm xúc đó."),
                cand("Having " + correct.lower(), "cấu trúc hoàn thành sai", "This sequence does not form a grammatical perfect participial clause.", "Chuỗi này không tạo thành mệnh đề phân từ hoàn thành đúng ngữ pháp."),
                cand("To " + correct.lower(), "động từ nguyên mẫu", "An infinitive would express purpose, not the team's reaction to the results.", "Động từ nguyên mẫu diễn tả mục đích, không phải phản ứng của nhóm trước kết quả."),
            ]
            rule_en = "A past-participial opening clause describes the passive cause or state affecting the subject of the main clause."
            rule_vi = "Mệnh đề mở đầu bằng quá khứ phân từ mô tả nguyên nhân hoặc trạng thái bị động tác động đến chủ ngữ mệnh đề chính."
            correct_index = 0

        elif category_index == 12:
            wh = [("why", "tại sao"), ("how", "bằng cách nào"), ("when", "khi nào"), ("where", "ở đâu"), ("why", "tại sao"), ("how", "bằng cách nào"), ("when", "khi nào"), ("where", "ở đâu"), ("why", "tại sao"), ("how", "bằng cách nào")][i]
            correct, correct_vi = wh
            stem = f"The {team} has not yet determined ______ the discrepancy in the {obj} occurred."
            stem_vi = f"{team_vi.capitalize()} vẫn chưa xác định được ______ sai lệch trong {obj_vi} xảy ra."
            candidates = [
                cand(correct, correct_vi, "This wh-expression introduces the missing information requested by “determined”.", "Từ/cụm từ hỏi này giới thiệu thông tin còn thiếu mà “determined” yêu cầu."),
                cand("did " + correct, "cấu trúc đảo của câu hỏi", "An embedded noun clause uses statement word order and does not take question inversion.", "Mệnh đề danh từ gián tiếp dùng trật tự câu trần thuật và không đảo như câu hỏi."),
                cand("that", "rằng", "“That” introduces a fact, but the sentence asks for unknown information about the discrepancy.", "“That” giới thiệu một sự thật, nhưng câu này hỏi thông tin chưa biết về sai lệch."),
                cand("because", "bởi vì", "“Because” introduces an adverbial reason clause, not the noun-clause object required after “determined”.", "“Because” mở đầu mệnh đề trạng ngữ chỉ nguyên nhân, không phải mệnh đề danh từ làm tân ngữ sau “determined”."),
            ]
            rule_en = f"The verb “determined” takes an embedded noun clause; “{correct}” supplies the unknown information with statement word order."
            rule_vi = f"Động từ “determined” nhận một mệnh đề danh từ gián tiếp; “{correct}” cung cấp thông tin chưa biết với trật tự câu trần thuật."
            correct_index = 0

        elif category_index == 13:
            connectors = [("Because", "Bởi vì"), ("Since", "Vì"), ("As", "Vì"), ("Given that", "Xét rằng"), ("Because", "Bởi vì"), ("Since", "Vì"), ("As", "Vì"), ("Given that", "Xét rằng"), ("Because", "Bởi vì"), ("Since", "Vì")]
            correct, correct_vi = connectors[i]
            stem = f"______ the {obj} remains confidential, only members of the {team} may access the supporting files."
            stem_vi = f"______ {obj_vi} vẫn được bảo mật, chỉ thành viên của {team_vi} mới được truy cập hồ sơ hỗ trợ."
            candidates = [
                cand(correct, correct_vi, "This subordinating expression supplies the intended relationship between the two clauses.", "Cụm liên kết phụ thuộc này thể hiện đúng quan hệ ý nghĩa giữa hai mệnh đề."),
                cand("Despite", "mặc dù", "“Despite” is a preposition and must be followed by a noun phrase or gerund, not this finite clause.", "“Despite” là giới từ và phải theo sau bởi cụm danh từ hoặc danh động từ, không phải mệnh đề hữu hạn này."),
                cand("Because of", "bởi vì", "“Because of” is a preposition; it cannot directly introduce “the ... remains”.", "“Because of” là giới từ; không thể trực tiếp mở đầu “the ... remains”."),
                cand("During", "trong suốt", "“During” takes a noun phrase and does not express the required clause relationship here.", "“During” đi với cụm danh từ và không thể hiện quan hệ mệnh đề cần thiết ở đây."),
            ]
            rule_en = f"“{correct}” functions as a subordinating conjunction and can introduce the complete clause before the comma."
            rule_vi = f"“{correct}” hoạt động như liên từ phụ thuộc và có thể mở đầu mệnh đề hoàn chỉnh trước dấu phẩy."
            correct_index = 0

        elif category_index == 14:
            pairs = [("because of", "do"), ("owing to", "do"), ("due to", "do"), ("on account of", "do"), ("as a result of", "do kết quả của"), ("because of", "do"), ("owing to", "do"), ("due to", "do"), ("on account of", "do"), ("as a result of", "do kết quả của")]
            correct, correct_vi = pairs[i]
            stem = f"The project managed by the {team} was postponed ______ a shortage of certified components."
            stem_vi = f"Dự án do {team_vi} quản lý đã bị hoãn ______ tình trạng thiếu linh kiện được chứng nhận."
            candidates = [
                cand(correct, correct_vi, "This multiword preposition can be followed by the noun phrase “a shortage”.", "Cụm giới từ này có thể theo sau bởi cụm danh từ “a shortage”."),
                cand("because", "bởi vì", "“Because” must introduce a complete clause, not the noun phrase “a shortage”.", "“Because” phải mở đầu mệnh đề hoàn chỉnh, không phải cụm danh từ “a shortage”."),
                cand("although", "mặc dù", "“Although” requires a finite clause and expresses concession rather than this noun-phrase link.", "“Although” cần mệnh đề hữu hạn và diễn tả nhượng bộ thay vì liên kết cụm danh từ này."),
                cand("therefore", "vì vậy", "“Therefore” is a conjunctive adverb and cannot directly govern a noun phrase.", "“Therefore” là trạng từ liên kết và không thể trực tiếp chi phối cụm danh từ."),
            ]
            rule_en = f"The blank is followed by a noun phrase, so the multiword preposition “{correct}” is grammatically appropriate."
            rule_vi = f"Sau chỗ trống là cụm danh từ, vì vậy cụm giới từ “{correct}” phù hợp về ngữ pháp."
            correct_index = 0

        elif category_index == 15:
            nouns = [("information", "thông tin"), ("equipment", "thiết bị"), ("advice", "lời khuyên"), ("research", "nghiên cứu"), ("evidence", "bằng chứng"), ("feedback", "phản hồi"), ("training", "đào tạo"), ("software", "phần mềm"), ("access", "quyền truy cập"), ("documentation", "tài liệu")]
            noun, noun_vi = nouns[i]
            stem = f"Before approving the {obj}, the {team} requested ______ additional {noun} from the contractor."
            stem_vi = f"Trước khi phê duyệt {obj_vi}, {team_vi} đã yêu cầu ______ {noun_vi} bổ sung từ nhà thầu."
            candidates = [
                cand("an", "một", f"“{noun}” is uncountable here, so it cannot take the singular article “an”.", f"“{noun}” là danh từ không đếm được ở đây nên không thể đi với mạo từ số ít “an”."),
                cand("a", "một", f"“{noun}” is uncountable here, so the singular article “a” is impossible.", f"“{noun}” là danh từ không đếm được ở đây nên mạo từ số ít “a” không thể dùng."),
                cand("some", "một số", "“Some” appropriately quantifies an unspecified amount of an uncountable noun.", "“Some” định lượng phù hợp một lượng không xác định của danh từ không đếm được."),
                cand("many", "nhiều", "“Many” is used with plural count nouns, not this uncountable noun.", "“Many” dùng với danh từ đếm được số nhiều, không dùng với danh từ không đếm được này."),
            ]
            rule_en = f"“{noun}” is uncountable in this meaning, and “some” can quantify an unspecified additional amount."
            rule_vi = f"“{noun}” là danh từ không đếm được trong nghĩa này và “some” có thể chỉ một lượng bổ sung không xác định."
            correct_index = 2

        elif category_index == 16:
            quantifiers = [("none", "không đề xuất nào"), ("each", "mỗi đề xuất"), ("either", "một trong hai"), ("neither", "không cái nào trong hai"), ("one", "một"), ("another", "một cái khác"), ("each", "mỗi đề xuất"), ("either", "một trong hai"), ("neither", "không cái nào trong hai"), ("one", "một")]
            correct, correct_vi = quantifiers[i]
            stem = f"Of the proposals reviewed by the {team}, ______ satisfies every mandatory condition in the {obj}."
            stem_vi = f"Trong số các đề xuất được {team_vi} xem xét, ______ đáp ứng mọi điều kiện bắt buộc trong {obj_vi}."
            candidates = [
                cand(correct, correct_vi, "This quantifier has the number and meaning needed by the context and singular verb “satisfies”.", "Lượng từ này có số và nghĩa phù hợp với ngữ cảnh và động từ số ít “satisfies”."),
                cand("they", "họ/chúng", "The plural pronoun conflicts with the singular verb “satisfies” and the partitive structure.", "Đại từ số nhiều xung đột với động từ số ít “satisfies” và cấu trúc bộ phận."),
                cand("them", "họ/chúng (tân ngữ)", "An object pronoun cannot function as the subject of “satisfies”.", "Đại từ tân ngữ không thể làm chủ ngữ của “satisfies”."),
                cand("any", "bất kỳ", "In this affirmative statement, bare “any” does not convey the intended exact quantity.", "Trong câu khẳng định này, “any” đứng một mình không truyền đạt lượng chính xác cần thiết."),
            ]
            rule_en = f"The partitive phrase “Of the proposals” requires a pronoun or quantifier that matches the intended quantity; “{correct}” also agrees with “satisfies”."
            rule_vi = f"Cụm bộ phận “Of the proposals” cần đại từ hoặc lượng từ phù hợp với số lượng dự định; “{correct}” cũng hòa hợp với “satisfies”."
            correct_index = 0

        elif category_index == 17:
            adjectives = [("reliable", "đáng tin cậy"), ("efficient", "hiệu quả"), ("accurate", "chính xác"), ("flexible", "linh hoạt"), ("secure", "an toàn"), ("detailed", "chi tiết"), ("profitable", "sinh lợi"), ("accessible", "dễ tiếp cận"), ("durable", "bền"), ("responsive", "nhanh nhạy")]
            adjective, adjective_vi = adjectives[i]
            stem = f"The revised {obj} is considerably ______ than the version previously used by the {team}."
            stem_vi = f"{obj_vi.capitalize()} sửa đổi ______ đáng kể so với phiên bản mà {team_vi} sử dụng trước đây."
            candidates = [
                cand(adjective, adjective_vi, "A bare adjective cannot follow “considerably” before the comparison marker “than”.", "Tính từ nguyên dạng không thể theo sau “considerably” trước dấu hiệu so sánh “than”."),
                cand("more " + adjective, adjective_vi + " hơn", "“More + adjective” forms the required comparative for this multisyllabic adjective.", "“More + tính từ” tạo dạng so sánh hơn cần thiết cho tính từ nhiều âm tiết này."),
                cand("most " + adjective, adjective_vi + " nhất", "The superlative “most” requires comparison with a whole group, not a single earlier version introduced by “than”.", "So sánh nhất “most” cần so với cả nhóm, không phải một phiên bản cũ được giới thiệu bằng “than”."),
                cand(adjective + "ly", "một cách " + adjective_vi, "The adverb form cannot serve as the comparative complement of “is”.", "Dạng trạng từ không thể làm bổ ngữ so sánh sau “is”."),
            ]
            rule_en = "“Considerably” intensifies a comparative, and “than” confirms that the structure requires “more + adjective”."
            rule_vi = "“Considerably” nhấn mạnh dạng so sánh hơn và “than” xác nhận cấu trúc cần “more + tính từ”."
            correct_index = 1

        elif category_index == 18:
            verbs = [("presenting", "present", "trình bày"), ("evaluating", "evaluate", "đánh giá"), ("summarizing", "summarize", "tóm tắt"), ("sharing", "share", "chia sẻ"), ("documenting", "document", "lập hồ sơ"), ("explaining", "explain", "giải thích"), ("reporting", "report", "báo cáo"), ("discussing", "discuss", "thảo luận"), ("interpreting", "interpret", "diễn giải"), ("reviewing", "review", "rà soát")]
            correct, base, correct_vi = verbs[i]
            stem = f"The position requires analyzing data, preparing recommendations, and ______ findings to the {team}."
            stem_vi = f"Vị trí này yêu cầu phân tích dữ liệu, chuẩn bị khuyến nghị và ______ các phát hiện cho {team_vi}."
            candidates = [
                cand(correct, correct_vi, "The gerund is parallel with “analyzing” and “preparing”.", "Danh động từ song song với “analyzing” và “preparing”."),
                cand("to " + base, "để " + correct_vi, "The to-infinitive breaks the established gerund parallelism.", "Động từ nguyên mẫu có “to” phá vỡ cấu trúc song song dạng danh động từ."),
                cand(base, correct_vi + " (nguyên mẫu)", "The bare form is not parallel with the two preceding -ing forms.", "Dạng nguyên mẫu không song song với hai dạng -ing đứng trước."),
                cand(base + "ed", "đã " + correct_vi, "A past-tense or participial form is not parallel with the coordinated gerunds.", "Dạng quá khứ hoặc phân từ không song song với các danh động từ được nối."),
            ]
            rule_en = "Items joined in a series after “requires” must use parallel grammatical forms; all three activities therefore use gerunds."
            rule_vi = "Các mục trong chuỗi sau “requires” phải có dạng ngữ pháp song song; vì vậy cả ba hoạt động đều dùng danh động từ."
            correct_index = 0

        else:
            collocations = [
                ("The finance team must comply", "with", "the revised reporting requirements", "tuân thủ"),
                ("The procurement department must account", "for", "every unexpected cost increase", "giải thích"),
                ("The operations committee will contribute", "to", "the implementation plan", "đóng góp vào"),
                ("The marketing division must adhere", "to", "the approved branding standards", "tuân theo"),
                ("Incomplete personnel records may result", "in", "processing delays", "dẫn đến"),
                ("The quality assurance group must refrain", "from", "sharing confidential files", "không làm"),
                ("The regional sales office may qualify", "for", "a volume discount", "đủ điều kiện nhận"),
                ("The legal affairs team plans to invest", "in", "upgraded document-security software", "đầu tư vào"),
                ("The customer support center must respond", "to", "every complaint within one business day", "phản hồi"),
                ("The final logistics review will consist", "of", "three separate stages", "bao gồm"),
            ]
            prefix, prep, complement, gloss = collocations[i]
            verb = prefix.split()[-1]
            stem = f"{prefix} ______ {complement}."
            stem_vi = f"Câu này cần giới từ cố định sau động từ “{verb}” để diễn tả nghĩa “{gloss}”."
            alternatives = [prep, "at", "on", "by"]
            candidates = []
            for option in alternatives:
                if option == prep:
                    candidates.append(cand(option, "giới từ đúng", f"“{verb} {prep}” is the established business-English collocation.", f"“{verb} {prep}” là kết hợp từ cố định trong tiếng Anh thương mại."))
                else:
                    candidates.append(cand(option, "giới từ không phù hợp", f"“{verb} {option}” is not the standard collocation for this meaning.", f"“{verb} {option}” không phải kết hợp từ chuẩn cho nghĩa này."))
            rule_en = f"The verb “{verb}” conventionally takes the preposition “{prep}” in this meaning."
            rule_vi = f"Động từ “{verb}” theo quy ước đi với giới từ “{prep}” trong nghĩa này."
            correct_index = alternatives.index(prep)

        questions.append(make_question(
            category_index, i, stem, stem_vi, candidates, correct_index,
            rule_en, rule_vi, cefr, difficulty, topic,
        ))
    return questions


def build() -> None:
    questions = [q for category_index in range(len(CATEGORIES)) for q in category_questions(category_index)]
    ids = [q["id"] for q in questions]
    fingerprints = [q["fingerprint"] for q in questions]
    assert len(questions) == 200
    assert len(ids) == len(set(ids))
    assert len(fingerprints) == len(set(fingerprints))
    assert all(len(q["options"]) == 4 for q in questions)
    assert all(sum(1 for o in q["options"] if o["correct"]) == 1 for q in questions)
    assert all(q["correctOptionId"] in "ABCD" for q in questions)

    taxonomy = {
        "schema": 1,
        "id": "test-taxonomy-v1",
        "contentUpdatedAt": GENERATED_AT,
        "examFamilies": [{"id": "toeic-lr", "label": "TOEIC Listening & Reading-style", "provider": "Original Study App practice"}],
        "cefrLevels": ["B1", "B2", "C1"],
        "difficultyLevels": [1, 2, 3, 4, 5],
        "categories": [
            {"id": cid, "parentId": "grammar", "label": study(en, vi), "description": study(f"Advanced workplace English practice for {en.lower()}.", f"Luyện tiếng Anh công sở nâng cao về {vi.lower()}.")}
            for cid, en, vi in CATEGORIES
        ],
    }
    pack = {
        "schema": 1,
        "id": "toeic-grammar-pack-0001",
        "version": 1,
        "status": "published",
        "examFamily": "toeic-lr",
        "questionType": "single-choice",
        "questionCount": len(questions),
        "contentUpdatedAt": GENERATED_AT,
        "immutability": "Published question IDs and versions must never be changed or reused.",
        "questions": questions,
    }
    fixed_ids = [f"toeic-g-{cid.split('.')[-1]}-001" for cid, _, _ in CATEGORIES]
    definition = {
        "schema": 1,
        "id": "toeic-grammar-advanced-001",
        "version": 1,
        "status": "published",
        "title": "Advanced TOEIC Grammar Test 1",
        "titleVi": "Bài kiểm tra ngữ pháp TOEIC nâng cao số 1",
        "description": study(
            "A 20-question original TOEIC Part 5-style grammar test covering every category in the initial bank.",
            "Bài kiểm tra ngữ pháp 20 câu theo phong cách TOEIC Part 5, bao quát mọi nhóm ngữ pháp trong ngân hàng ban đầu.",
        ),
        "testType": "language",
        "examFamily": "toeic-lr",
        "examPart": "reading-part-5",
        "testNumber": 1,
        "testDate": "2026-08-25",
        "questionCount": 20,
        "durationMinutes": 15,
        "defaultMode": "training",
        "supportedModes": ["training", "exam"],
        "targetToeicRange": {"min": 700, "max": 990},
        "scorePolicy": "raw-percent-not-official-toeic-scale",
        "questionIds": fixed_ids,
        "packIds": [pack["id"]],
        "contentUpdatedAt": GENERATED_AT,
    }

    by_category = Counter(q["primaryCategoryId"] for q in questions)
    by_cefr = Counter(q["cefr"] for q in questions)
    by_difficulty = Counter(str(q["difficulty"]) for q in questions)
    by_answer = Counter(q["correctOptionId"] for q in questions)
    stats = {
        "schema": 1,
        "id": "test-bank-stats-v1",
        "generatedAt": GENERATED_AT,
        "totalQuestions": len(questions),
        "publishedQuestions": len(questions),
        "packCount": 1,
        "testDefinitionCount": 1,
        "duplicateIds": 0,
        "duplicateFingerprints": 0,
        "invalidQuestions": 0,
        "byCategory": dict(sorted(by_category.items())),
        "byCefr": dict(sorted(by_cefr.items())),
        "byDifficulty": dict(sorted(by_difficulty.items())),
        "correctOptionDistribution": dict(sorted(by_answer.items())),
    }

    PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFINITION_PATH.parent.mkdir(parents=True, exist_ok=True)
    for path, payload in [
        (TAXONOMY_PATH, taxonomy),
        (PACK_PATH, pack),
        (DEFINITION_PATH, definition),
        (STATS_PATH, stats),
    ]:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    file_rows = []
    for path in [TAXONOMY_PATH, PACK_PATH, DEFINITION_PATH, STATS_PATH]:
        raw = path.read_bytes()
        file_rows.append({
            "id": json.loads(raw)["id"],
            "path": path.relative_to(TEST_ROOT).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        })
    manifest = {
        "schema": 1,
        "id": "test-bank-manifest-v1",
        "contentVersion": hashlib.sha256(json.dumps(file_rows, sort_keys=True).encode("utf-8")).hexdigest(),
        "contentUpdatedAt": GENERATED_AT,
        "taxonomyPath": "taxonomy.json",
        "statsPath": "bank-stats.json",
        "packs": [{"id": pack["id"], "path": PACK_PATH.relative_to(TEST_ROOT).as_posix(), "questionCount": 200, "version": 1}],
        "tests": [{"id": definition["id"], "path": DEFINITION_PATH.relative_to(TEST_ROOT).as_posix(), "questionCount": 20, "version": 1, "title": definition["title"], "titleVi": definition["titleVi"], "examFamily": "toeic-lr", "targetToeicRange": definition["targetToeicRange"], "durationMinutes": 15}],
        "files": file_rows,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(questions)} stable questions, {len(CATEGORIES)} categories, and one 20-question fixed test.")
    print(f"Correct answer distribution: {dict(sorted(by_answer.items()))}")


if __name__ == "__main__":
    build()
