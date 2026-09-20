FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY solution.py database.py app_ui.py README.md ./
COPY inbox ./inbox
COPY attachments ./attachments

EXPOSE 8501
CMD ["streamlit", "run", "app_ui.py"]