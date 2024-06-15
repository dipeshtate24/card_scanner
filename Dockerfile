# FROM python:3.11-slim-buster

# RUN apt-get update && \
#     apt-get -qq -y install tesseract-ocr && \
#     apt-get -qq -y install libtesseract-dev

# WORKDIR /app

# COPY requirements.txt requirements.txt
# RUN pip3 install -r requirements.txt

# COPY . .

# CMD ["gunicorn", "Final_main:app"]

FROM python:3.9-slim

# Install Tesseract OCR and language pack
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Set the Tesseract executable path environment variable
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "Final_main.py"]
