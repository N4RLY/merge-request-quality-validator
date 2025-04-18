FROM python:3.12-slim

WORKDIR /app

# Copy requirements and project configuration
COPY pyproject.toml .
COPY uv.lock .
COPY README.md .

# Copy application files
COPY main.py .
COPY repository_parser.py .
COPY app/ ./app/

# Install dependencies
RUN pip install --no-cache-dir uv
RUN uv pip install --system .

# Expose the port Gradio runs on
EXPOSE 7860

# Command to run the Gradio interface
CMD ["python", "-m", "app.gradio_ui"] 