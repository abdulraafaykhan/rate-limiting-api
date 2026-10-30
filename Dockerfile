# Small Python image keeps the build fast.
FROM python:3.12-slim

# All project files live here inside the container.
WORKDIR /code

# Copy requirements first so Docker can cache the install step.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code last (it changes most often).
COPY app ./app

# Listen on all interfaces so other containers can reach the API.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
