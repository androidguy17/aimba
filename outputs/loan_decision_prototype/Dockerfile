FROM python:3.13-slim
WORKDIR /app
COPY *.py *.json *.md *.css ./
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["python", "app.py"]
