from django.urls import path
from .views import PDFIngestionAPIView, ChatbotAPIView, CrawlerAPIView

urlpatterns = [
    path('api/pdf/ingest/', PDFIngestionAPIView.as_view(), name='pdf_ingestion'),
    path('api/chatbot/query/', ChatbotAPIView.as_view(), name='chatbot_query'),
    path('api/crawler/ingest/', CrawlerAPIView.as_view(), name='crawler_ingest'),
]
