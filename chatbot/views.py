from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os

from .services.pdf_ingestion_service import ingest_pdf
from .services.chatbot_service import get_chatbot_response
from .services.crawler_service import ingest_website


class PDFIngestionAPIView(APIView):
    """
    API endpoint for PDF ingestion.
    Accepts PDF file upload and tenant_id.
    """
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_description="Upload a PDF file to ingest its content into the vector database. The PDF will be processed, chunked, and embedded for RAG (Retrieval Augmented Generation) purposes.",
        manual_parameters=[
            openapi.Parameter(
                'pdf_file',
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description='PDF file to upload and ingest'
            ),
            openapi.Parameter(
                'tenant_id',
                openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=True,
                description='Tenant identifier for multi-tenancy support'
            ),
        ],
        responses={
            200: openapi.Response(
                description='PDF ingested successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'file_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'tenant_id': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(description='Bad request - missing required fields'),
            500: openapi.Response(description='Internal server error'),
        },
        tags=['PDF Ingestion']
    )
    
    def post(self, request):
        try:
            # Get PDF file from request
            pdf_file = request.FILES.get('pdf_file')
            tenant_id = request.data.get('tenant_id')
            
            if not pdf_file:
                return Response(
                    {'error': 'PDF file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not tenant_id:
                return Response(
                    {'error': 'tenant_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Save uploaded file temporarily
            file_path = default_storage.save(
                f'temp_pdfs/{pdf_file.name}',
                ContentFile(pdf_file.read())
            )
            full_path = default_storage.path(file_path)
            
            try:
                # Ingest PDF
                ingest_pdf(full_path, tenant_id)
                
                return Response(
                    {
                        'message': 'PDF ingested successfully',
                        'file_name': pdf_file.name,
                        'tenant_id': tenant_id
                    },
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            finally:
                # Clean up temporary file
                if os.path.exists(full_path):
                    os.remove(full_path)
                    # Remove directory if empty
                    try:
                        os.rmdir(os.path.dirname(full_path))
                    except OSError:
                        pass
                        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatbotAPIView(APIView):
    """
    API endpoint for chatbot queries.
    Accepts question and tenant_id.
    """
    parser_classes = [JSONParser]
    
    @swagger_auto_schema(
        operation_description="Query the chatbot with a question. The system will retrieve relevant context from the vector database and generate an answer using RAG (Retrieval Augmented Generation).",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['question', 'tenant_id'],
            properties={
                'question': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The question to ask the chatbot'
                ),
                'tenant_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Tenant identifier for multi-tenancy support'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description='Chatbot response',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'question': openapi.Schema(type=openapi.TYPE_STRING),
                        'answer': openapi.Schema(type=openapi.TYPE_STRING),
                        'tenant_id': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(description='Bad request - missing required fields'),
            500: openapi.Response(description='Internal server error'),
        },
        tags=['Chatbot']
    )
    
    def post(self, request):
        try:
            question = request.data.get('question')
            tenant_id = request.data.get('tenant_id')
            
            if not question:
                return Response(
                    {'error': 'question is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not tenant_id:
                return Response(
                    {'error': 'tenant_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get chatbot response
            answer = get_chatbot_response(question, tenant_id)
            
            return Response(
                {
                    'question': question,
                    'answer': answer,
                    'tenant_id': tenant_id
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CrawlerAPIView(APIView):
    """
    API endpoint for website crawling.
    Accepts website URL and tenant_id.
    """
    parser_classes = [JSONParser]
    
    @swagger_auto_schema(
        operation_description="Crawl a website starting from the given URL. The crawler will extract content from web pages, process it, and store it in the vector database for RAG purposes. Uses Selenium for JavaScript-heavy sites.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['website_url', 'tenant_id'],
            properties={
                'website_url': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_URI,
                    description='Starting URL for website crawling'
                ),
                'tenant_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Tenant identifier for multi-tenancy support'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description='Website crawled successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'website_url': openapi.Schema(type=openapi.TYPE_STRING),
                        'tenant_id': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(description='Bad request - missing required fields'),
            500: openapi.Response(description='Internal server error'),
        },
        tags=['Crawler']
    )
    
    def post(self, request):
        try:
            website_url = request.data.get('website_url')
            tenant_id = request.data.get('tenant_id')
            
            if not website_url:
                return Response(
                    {'error': 'website_url is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not tenant_id:
                return Response(
                    {'error': 'tenant_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ingest website
            ingest_website(website_url, tenant_id)
            
            return Response(
                {
                    'message': 'Website crawled and ingested successfully',
                    'website_url': website_url,
                    'tenant_id': tenant_id
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
