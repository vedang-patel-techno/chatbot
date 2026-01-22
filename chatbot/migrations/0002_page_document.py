# Generated migration for Page and Document models

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0001_initial'),
    ]

    operations = [
        # Create pgvector extension
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;"
        ),
        # Create pages table
        migrations.RunSQL(
            """
            CREATE TABLE IF NOT EXISTS pages (
                id SERIAL PRIMARY KEY,
                url TEXT UNIQUE,
                tenant_id TEXT,
                content_hash TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                last_indexed TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url);
            CREATE INDEX IF NOT EXISTS idx_pages_tenant_id ON pages(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_pages_tenant_active ON pages(tenant_id, is_active);
            """,
            reverse_sql="DROP TABLE IF EXISTS pages;"
        ),
        # Create documents table with vector field
        migrations.RunSQL(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                content TEXT,
                source TEXT,
                page_url TEXT,
                embedding vector(768),
                hash TEXT UNIQUE
            );
            CREATE INDEX IF NOT EXISTS idx_documents_page_url ON documents(page_url);
            CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(hash);
            """,
            reverse_sql="DROP TABLE IF EXISTS documents;"
        ),
    ]

