FROM python:3.12-slim

WORKDIR /app

# Copy only required source files and assets, exclude tests and test configs
COPY bot.py expenseimage.py sheets_api.py keywords.json reminders.json types_data.json config.env config_cloud.env /app/
COPY Courier.ttc /Courier.ttc

RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8080

CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "8080"]