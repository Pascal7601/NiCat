"""Search only rights-cleared and reviewer-approved excerpts in the same topic.

PostgreSQL uses native full-text ranking; SQLite tests use lexical overlap.
No private student submissions, answer keys, or uploaded unreviewed files enter retrieval.
"""
import re
from functools import reduce
from operator import or_

from django.db import connection
from django.db.models import Q

from .models import SourceExcerpt

STOPWORDS = {
    "about", "after", "also", "answer", "between", "compare", "define", "describe",
    "difference", "discuss", "each", "example", "explain", "from", "give", "how",
    "into", "more", "question", "that", "their", "them", "these", "this", "using",
    "what", "when", "which", "while", "with", "would", "your", "should", "provide",
}


def search_terms(question: str, topic_title: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", f"{topic_title} {question}".lower())
    return list(dict.fromkeys(w for w in words if w not in STOPWORDS))[:12]


def retrieve_excerpts(*, revision, limit: int = 5) -> list[SourceExcerpt]:
    topic = revision.question.topic
    candidates = SourceExcerpt.objects.filter(
        topic=topic, state=SourceExcerpt.State.APPROVED,
        reference__document__rights_status="allowed", reference__document__unit_id=topic.unit_id,
    ).select_related("reference__document", "topic")
    tokens = search_terms(revision.prompt, topic.title)
    if not tokens:
        return []
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        query = reduce(or_, (SearchQuery(w, config="english") for w in tokens))
        return list(candidates.annotate(
            match_rank=SearchRank(SearchVector("text", config="english"), query)
        ).filter(match_rank__gt=0.001).order_by("-match_rank", "pk")[:limit])
    # Local SQLite fallback is deterministic, bounded and always topic-filtered.
    word_filter = reduce(or_, (Q(text__icontains=w) for w in tokens))
    records = list(candidates.filter(word_filter)[:100])
    records.sort(key=lambda e: (-sum(w in e.text.lower() for w in tokens), str(e.pk)))
    return records[:limit]
