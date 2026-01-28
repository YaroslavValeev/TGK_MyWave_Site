from flask import Blueprint, request, jsonify, current_app
import logging

from app.services.openai_service import get_embedding_vector
from app.ai.rag_store import get_rag_store

rag_bp = Blueprint("rag", __name__, url_prefix="/api/rag")
logger = logging.getLogger(__name__)


@rag_bp.route("/search", methods=["POST"])
def rag_search():
    if not current_app.config.get("ENABLE_RAG"):
        return jsonify({"error": "RAG disabled"}), 503

    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query required"}), 400

    try:
        q_emb = get_embedding_vector(query)
    except Exception as e:
        logger.exception("[RAG] embedding error: %s", e)
        return jsonify({"error": "embedding_error"}), 500

    try:
        store = get_rag_store()
        docs = store.search(q_emb, top_k=int(data.get("top_k", 5)))
    except Exception as e:
        logger.exception("[RAG] search error: %s", e)
        return jsonify({"error": "search_error"}), 500

    return jsonify(
        {
            "results": [
                {
                    "id": d.id,
                    "source": d.source,
                    "title": d.title,
                    "tags": d.tags,
                    "snippet": (d.text or "")[:300],
                }
                for d in docs
            ]
        }
    )


