# Download the Debian and Python Docker images to the container.
FROM python:latest

# Make a directory for the app
RUN mkdir -p /Web_Crawler

# Change the work directory to the created folder.
WORKDIR /Web_Crawler

# Copy the pip installation requirements to the container
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./main.py"]