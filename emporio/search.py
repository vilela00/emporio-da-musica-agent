"""Catalog search: category words in Portuguese, fuzzy model names, price filters."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from decimal import Decimal

from emporio.catalog import Category, Product, Store, normalize
from emporio.pricing import priced

CATEGORY_WORDS = {
    1: ("guitarra", "guitarras"),
    2: ("baixo", "baixos", "contrabaixo", "contrabaixos"),
    3: ("bateria", "baterias", "percussao"),
    4: ("teclado", "teclados", "piano", "pianos", "sintetizador", "sintetizadores", "synth"),
    5: ("violao", "violoes"),
    6: ("sopro", "flauta", "flautas", "clarinete", "clarinetes", "saxofone", "saxofones", "sax", "oboe"),
    7: ("trompete", "trompetes", "trombone", "trombones", "tuba", "tubas", "trompa", "trompas"),
    8: ("violino", "violinos", "viola", "violas", "violoncelo", "violoncelos", "cello"),
    9: ("ukulele", "ukuleles", "uke"),
}
STOPWORDS = {"de", "do", "da", "dos", "das", "o", "a", "os", "as", "um", "uma", "para", "pra", "com", "e", "em"}
STRINGS_WORDS = {"steel": "aco cordas de aco", "nylon": "nylon cordas de nylon"}


def resolve_category(store: Store, text: str) -> Category | None:
    words = normalize(text).split()
    for category_id, synonyms in CATEGORY_WORDS.items():
        if any(w in synonyms for w in words):
            return store.categories[category_id]
    target = normalize(text)
    return next((c for c in store.categories.values() if normalize(c.name) == target), None)


def search_text(store: Store, product: Product) -> str:
    """Name, category and specs in Portuguese; the description only when it is trustworthy (A-01)."""
    parts = [product.name, store.categories[product.category_id].name]
    strings = product.specs.get("strings", "")
    parts.append(STRINGS_WORDS.get(strings, ""))
    if product.specs.get("electronics") == "yes":
        parts.append("eletrico eletroacustico captacao")
    if not product.description_conflict:
        parts.append(product.description)
    return normalize(" ".join(parts))


def score(store: Store, product: Product, query: str) -> float:
    q = re.sub(r"(?<=[a-z]) (?=\d)", "", normalize(query))  # 'gd 20' -> 'gd20'
    name = normalize(product.name)
    if q and q.replace(" ", "") in name.replace(" ", ""):
        return 1.0  # 'takamine gd20', 'gd 20', 'c40'
    tokens = [t for t in q.split() if t not in STOPWORDS]
    if not tokens:
        return 0.0
    vocabulary = set(search_text(store, product).split())

    def hit(token: str) -> bool:
        if token in vocabulary or any(len(token) >= 4 and v.startswith(token[:-1]) for v in vocabulary):
            return True
        return bool(difflib.get_close_matches(token, vocabulary, n=1, cutoff=0.85))

    return sum(hit(t) for t in tokens) / len(tokens)


@dataclass(frozen=True)
class SearchResult:
    shown: list[Product]
    total: int
    unavailable_matches: list[Product]
    category: Category | None
    relaxed: bool = False  # nothing matched the words, so the whole category is shown


def search(
    store: Store,
    *,
    query: str = "",
    category: str = "",
    max_price: Decimal | None = None,
    min_price: Decimal | None = None,
    only_available: bool = True,
    limit: int = 10,
) -> SearchResult:
    cat = resolve_category(store, category or query) if (category or query) else None
    if query and cat:
        query = " ".join(w for w in normalize(query).split() if w not in CATEGORY_WORDS[cat.id])

    def price_ok(product: Product) -> bool:
        price = priced(store, product).unit_price
        return (max_price is None or price <= max_price) and (min_price is None or price >= min_price)

    candidates = [
        p for p in store.products.values()
        if (cat is None or p.category_id == cat.id) and price_ok(p)
    ]
    by_price = sorted(candidates, key=lambda p: priced(store, p).unit_price)
    relaxed = False
    if query.strip():
        scored = [(score(store, p, query), p) for p in by_price]
        best = max((s for s, _ in scored), default=0.0)
        # Only the best tier: 'nylon iniciante' should not bring steel-string guitars that merely say 'iniciante'.
        matched = [p for s, p in scored if s >= 0.5 and s == best]
        relaxed = not matched and cat is not None
        candidates = by_price if relaxed else matched
    else:
        candidates = by_price

    available = [p for p in candidates if p.is_available]
    unavailable = [p for p in candidates if not p.is_available]
    pool = available if only_available else candidates
    return SearchResult(pool[:limit], len(pool), unavailable if only_available else [], cat, relaxed)


def alternatives(store: Store, product: Product, limit: int = 3) -> list[Product]:
    """Same category, available, same string type when possible, closest price first (manual §7.3)."""
    pool = [
        p for p in store.products.values()
        if p.category_id == product.category_id and p.is_available and p.id != product.id
    ]
    same_strings = [p for p in pool if p.specs.get("strings") == product.specs.get("strings")]
    return sorted(same_strings or pool, key=lambda p: abs(p.price - product.price))[:limit]
