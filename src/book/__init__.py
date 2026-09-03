"""The locked equity book -- the only real source of truth in this product.

The engine never picks a name. A human writes `config/book.yaml`; this
package loads it, matches incoming news against it, and nothing else in
the codebase is allowed to add a name, change a role, or invent a thesis.
"""
from __future__ import annotations

from src.book.loader import DEFAULT_BOOK_PATH, load_book
from src.book.match import keep_book_relevant, match_all
from src.book.models import Book, Name, Sleeve

__all__ = [
    "Book",
    "Name",
    "Sleeve",
    "DEFAULT_BOOK_PATH",
    "load_book",
    "match_all",
    "keep_book_relevant",
]
