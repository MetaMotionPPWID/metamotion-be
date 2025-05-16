FROM python:3.13

WORKDIR /app

COPY . .
RUN pip install -r requirements.txt

CMD ["python", "-m", "flask", "--app", "app.main", "run", "--host=0.0.0.0", "--port=8000"]
