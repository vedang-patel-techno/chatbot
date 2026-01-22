from django.db import models
from django.utils import timezone


class Page(models.Model):
    """
    Model representing a page (URL) that has been indexed.
    """
    url = models.TextField(unique=True, db_index=True)
    tenant_id = models.TextField(db_index=True)
    content_hash = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)
    last_indexed = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'pages'
        indexes = [
            models.Index(fields=['tenant_id', 'is_active']),
            models.Index(fields=['url']),
        ]
    
    def __str__(self):
        return f"{self.url} ({self.tenant_id})"


class Document(models.Model):
    """
    Model representing a document chunk with its embedding.
    Note: The embedding field uses PostgreSQL's vector type (768 dimensions).
    This requires the pgvector extension to be installed.
    """
    content = models.TextField()
    source = models.TextField()
    page_url = models.TextField(db_index=True)
    # embedding is stored as a vector(768) in PostgreSQL
    # We'll use a TextField to store it as JSON, or use raw SQL for vector operations
    embedding = models.TextField(help_text="Vector embedding stored as JSON array")
    hash = models.TextField(unique=True, db_index=True)
    
    class Meta:
        db_table = 'documents'
        indexes = [
            models.Index(fields=['page_url']),
            models.Index(fields=['hash']),
        ]
    
    def __str__(self):
        return f"Document {self.id} from {self.source}"
