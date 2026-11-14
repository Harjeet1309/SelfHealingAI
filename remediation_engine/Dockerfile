FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY remediation_engine ./remediation_engine

# Port 5001 is used by webhook_server.py (Alertmanager -> Remediation webhook)
EXPOSE 5001

# Entry point: V4 LSTM inference engine (corroboration, rules, online learning)
CMD ["python", "-m", "remediation_engine.ai.inference"]