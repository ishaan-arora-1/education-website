# Python base image
FROM python:3.10-slim@sha256:f9fd9a142c9e3bc54d906053b756eb7e7e386ee1cf784d82c251cf640c502512

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifests first (better layer caching)
COPY pyproject.toml poetry.lock* ./

# Install Poetry and project dependencies (system deps minimal here; app build image)
RUN python -m pip install --upgrade pip wheel setuptools && \
    pip install poetry==1.8.3 && \
    poetry config virtualenvs.create false --local || true && \
    poetry install --only main --no-interaction --no-ansi

# Copy project files
COPY . .

# Create necessary directories for static files
RUN mkdir -p /app/static /app/staticfiles

# Create and configure environment variables
COPY .env.sample .env

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations and create test data
RUN python manage.py migrate && \
    python manage.py create_test_data

# Create superuser
ENV DJANGO_SUPERUSER_USERNAME=admin
ENV DJANGO_SUPERUSER_EMAIL=admin@example.com
ENV DJANGO_SUPERUSER_PASSWORD=adminpassword
RUN python manage.py createsuperuser --noinput

# Echo message during build
RUN echo "Your Project is now live on http://localhost:8000"

# Expose port
EXPOSE 8000

# Start the server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
