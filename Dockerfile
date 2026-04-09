# DevOps AI Agent - Docker Image
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY devops_agent.py .
COPY auth.py .
COPY manage_users.py .
COPY templates/ templates/
COPY tools/ tools/
COPY knowledge/ knowledge/

RUN mkdir -p /app/kubeconfigs /app/data

EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=devops_agent.py

CMD ["python", "devops_agent.py"]
