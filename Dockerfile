FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /Blog

RUN 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install django-redis==5.4.0
RUN pip install --no-cache-dir gunicorn

COPY . .

CMD ["gunicorn", "Blog.wsgi:application", "--bind", "0.0.0.0:8000"]