FROM python:3.14-slim

# Don't buffer stdout and stderr, and don't create .pyc files
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /ephemera

# Copy the requirements into the /ephemera directory inside the container
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y build-essential libpq-dev \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Copy all of the current directory into the /ephemera directory inside the container
COPY . .

# Install the project as a package inside the container, so that the test code can properly run.
RUN pip install --no-cache-dir -e .

# Expose port 8000 so that localhost can reach the backend.
EXPOSE 8000

ENV PYTHONPATH=/ephemera

CMD ["python", "src/manage.py", "runserver", "0.0.0.0:8000"]