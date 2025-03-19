import os
import json
import sqlite3
import numpy as np
from datetime import datetime
import hashlib
from openai import OpenAI
import uuid
from pathlib import Path

class KnowledgeBase:
    def __init__(self, db_path="knowledge.db", embedding_model="text-embedding-3-small", api_key=None):
        """Initialize the knowledge base with SQLite database and OpenAI embedding model."""
        self.db_path = db_path
        self.embedding_model = embedding_model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set as OPENAI_API_KEY environment variable")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Create data directory if it doesn't exist
        data_dir = os.path.dirname(db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database with necessary tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create documents table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                source TEXT,
                metadata TEXT,
                created_at TEXT,
                accessed_at TEXT,
                access_count INTEGER DEFAULT 0
            )
            ''')
            
            # Create embeddings table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                embedding BLOB,
                created_at TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
            ''')
            
            # Create conversations table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_query TEXT,
                assistant_response TEXT,
                context_ids TEXT,
                created_at TEXT
            )
            ''')
            
            conn.commit()
    
    def _get_embedding(self, text):
        """Generate embedding vector for the given text using OpenAI API."""
        # Clean and truncate text if needed (OpenAI has token limits)
        clean_text = text.strip().replace("\n", " ")
        
        # Get embedding from OpenAI
        response = self.client.embeddings.create(
            input=clean_text,
            model=self.embedding_model
        )
        
        # Extract embedding from response
        embedding = response.data[0].embedding
        
        return embedding
    
    def add_document(self, content, title=None, source=None, metadata=None):
        """Add a document to the knowledge base with its embedding."""
        # Generate a unique ID
        doc_id = str(uuid.uuid4())
        
        # Generate title if not provided
        if not title:
            title = content[:50] + ("..." if len(content) > 50 else "")
        
        # Current timestamp
        timestamp = datetime.now().isoformat()
        
        # Store the document
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert document
            cursor.execute(
                "INSERT INTO documents (id, title, content, source, metadata, created_at, accessed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (doc_id, title, content, source, json.dumps(metadata or {}), timestamp, timestamp)
            )
            
            # Generate and store embedding
            embedding = self._get_embedding(content)
            embedding_bytes = np.array(embedding).tobytes()
            
            cursor.execute(
                "INSERT INTO embeddings (id, document_id, embedding, created_at) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), doc_id, embedding_bytes, timestamp)
            )
            
            conn.commit()
        
        return doc_id
    
    def retrieve_document(self, doc_id):
        """Retrieve a document by its ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Update access stats
            timestamp = datetime.now().isoformat()
            cursor.execute(
                "UPDATE documents SET accessed_at = ?, access_count = access_count + 1 WHERE id = ?",
                (timestamp, doc_id)
            )
            
            # Retrieve document
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            result = cursor.row_factory(cursor, cursor.fetchone())
            
            if result:
                # Convert to dictionary
                doc = dict(result)
                doc['metadata'] = json.loads(doc['metadata'])
                return doc
            
            return None
    
    def retrieve_similar(self, query, limit=5):
        """Retrieve documents similar to the query."""
        # Generate embedding for the query
        query_embedding = self._get_embedding(query)
        query_embedding_array = np.array(query_embedding)
        
        # Retrieve all documents and their embeddings
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT d.id, d.title, d.content, d.source, d.metadata, e.embedding
                FROM documents d
                JOIN embeddings e ON d.id = e.document_id
            ''')
            
            results = []
            for row in cursor.fetchall():
                doc = dict(row)
                embedding_bytes = doc.pop('embedding')
                doc_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                
                # Calculate cosine similarity
                similarity = np.dot(query_embedding_array, doc_embedding) / (
                    np.linalg.norm(query_embedding_array) * np.linalg.norm(doc_embedding)
                )
                
                doc['similarity'] = float(similarity)
                doc['metadata'] = json.loads(doc['metadata'])
                results.append(doc)
            
            # Sort by similarity and take top 'limit'
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:limit]
    
    def delete_document(self, doc_id):
        """Delete a document and its embedding."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete embedding first due to foreign key constraint
            cursor.execute("DELETE FROM embeddings WHERE document_id = ?", (doc_id,))
            
            # Delete document
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            
            conn.commit()
            
            return cursor.rowcount > 0
    
    def log_conversation(self, user_query, assistant_response, context_ids=None):
        """Log a conversation with the context documents used."""
        conv_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Convert context_ids to JSON string if provided
        context_ids_str = json.dumps(context_ids) if context_ids else "[]"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO conversations (id, user_query, assistant_response, context_ids, created_at) VALUES (?, ?, ?, ?, ?)",
                (conv_id, user_query, assistant_response, context_ids_str, timestamp)
            )
            
            conn.commit()
        
        return conv_id
    
    def search_documents(self, query, field="content", limit=10):
        """Search documents using simple text search."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Simple keyword search
            search_query = f"%{query}%"
            cursor.execute(
                f"SELECT * FROM documents WHERE {field} LIKE ? ORDER BY created_at DESC LIMIT ?",
                (search_query, limit)
            )
            
            results = []
            for row in cursor.fetchall():
                doc = dict(row)
                doc['metadata'] = json.loads(doc['metadata'])
                results.append(doc)
            
            return results
    
    def get_document_count(self):
        """Get the total number of documents in the knowledge base."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            return cursor.fetchone()[0]
            
    def get_recent_documents(self, limit=10):
        """Get the most recently added documents."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM documents ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            
            results = []
            for row in cursor.fetchall():
                doc = dict(row)
                doc['metadata'] = json.loads(doc['metadata'])
                results.append(doc)
            
            return results
    
    def get_rag_context(self, query, max_tokens=1500):
        """Get RAG context for a query, formatted for insertion into a prompt."""
        similar_docs = self.retrieve_similar(query)
        
        context = "Knowledge Base Context:\n"
        total_length = 0
        used_docs = []
        
        for doc in similar_docs:
            doc_content = doc['content']
            # Approximate token count (1 token ≈ 4 characters)
            doc_tokens = len(doc_content) / 4
            
            if total_length + doc_tokens > max_tokens:
                # Truncate if needed
                available_tokens = max_tokens - total_length
                available_chars = int(available_tokens * 4)
                if available_chars > 100:  # Only add if we can include meaningful content
                    doc_content = doc_content[:available_chars] + "..."
                    context += f"\n--- Document: {doc['title']} ---\n{doc_content}\n"
                    used_docs.append(doc['id'])
                break
            
            context += f"\n--- Document: {doc['title']} ---\n{doc_content}\n"
            total_length += doc_tokens
            used_docs.append(doc['id'])
            
            if total_length >= max_tokens:
                break
        
        return context, used_docs 