"""Unit tests for Safari RAG retrieval helper."""
import pytest
from app.services.safari_rag import retrieve_by_keyword, build_rag_prompt
from app.database.models import Document, db


@pytest.fixture(autouse=True)
def setup_docs(app):
    """Create test documents for RAG retrieval tests."""
    with app.app_context():
        db.create_all()
        
        # Create test documents
        doc1 = Document(
            title='Route R1',
            content='Beautiful mountain route with scenic views. Great for beginners.',
            meta={'type': 'route', 'collection': 'safari', 'difficulty': 'beginner'}
        )
        doc2 = Document(
            title='What to bring',
            content='Bring swimwear, sunscreen, and a towel for the safari trip.',
            meta={'type': 'faq', 'collection': 'safari', 'category': 'preparation'}
        )
        doc3 = Document(
            title='Advanced Techniques',
            content='Learn how to perform aerial tricks and advanced maneuvers.',
            meta={'type': 'guide', 'collection': 'wakesurf'}
        )
        
        db.session.add(doc1)
        db.session.add(doc2)
        db.session.add(doc3)
        db.session.commit()
        
        yield
        
        db.session.query(Document).delete()
        db.session.commit()
        db.drop_all()


def test_retrieve_by_keyword_returns_matching_docs(app):
    """Test that retrieve_by_keyword returns documents matching the keyword."""
    with app.app_context():
        results = retrieve_by_keyword('route', k=5)
        
        assert len(results) >= 1, "Should find at least one document with 'route'"
        # Should find 'Route R1'
        titles = [r['title'] for r in results]
        assert any('route' in t.lower() for t in titles), "Should find doc with 'route' in title"


def test_retrieve_by_keyword_respects_k_limit(app):
    """Test that retrieve_by_keyword respects the k parameter."""
    with app.app_context():
        results = retrieve_by_keyword('safari', k=1)
        
        assert len(results) <= 1, "Should return at most k=1 document"


def test_retrieve_by_keyword_empty_keyword_returns_empty(app):
    """Test that empty keyword returns empty list."""
    with app.app_context():
        results = retrieve_by_keyword('', k=10)
        
        assert results == [], "Empty keyword should return empty list"


def test_retrieve_by_keyword_no_match_returns_empty(app):
    """Test that non-matching keyword returns empty list."""
    with app.app_context():
        results = retrieve_by_keyword('nonexistent_xyz_keyword', k=10)
        
        assert results == [], "Non-matching keyword should return empty list"


def test_build_rag_prompt_concatenates_contexts(app):
    """Test that build_rag_prompt properly concatenates contexts."""
    contexts = [
        {'title': 'Doc1', 'content': 'Content of doc 1'},
        {'title': 'Doc2', 'content': 'Content of doc 2'}
    ]
    
    prompt = build_rag_prompt('What is the best route?', contexts)
    
    assert 'Doc1' in prompt, "Should include first document title"
    assert 'Doc2' in prompt, "Should include second document title"
    assert 'What is the best route?' in prompt, "Should include user question"
    assert 'Context' in prompt, "Should have context prefix"


def test_build_rag_prompt_truncates_long_content(app):
    """Test that build_rag_prompt truncates very long content."""
    long_content = 'x' * 1000
    contexts = [{'title': 'Long', 'content': long_content}]
    
    prompt = build_rag_prompt('Question', contexts)
    
    # Content should be truncated to 600 chars, so total length should be reasonable
    assert len(prompt) < 2000, "Prompt should be reasonably sized even with long context"


def test_retrieve_returns_document_structure(app):
    """Test that retrieved documents have expected structure."""
    with app.app_context():
        results = retrieve_by_keyword('bring', k=5)
        
        assert len(results) > 0, "Should find document with 'bring'"
        doc = results[0]
        
        assert 'id' in doc, "Document should have id"
        assert 'title' in doc, "Document should have title"
        assert 'content' in doc, "Document should have content"
        assert 'meta' in doc, "Document should have meta"
        assert isinstance(doc['meta'], dict), "Meta should be a dict"
