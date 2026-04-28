# Use a lightweight Linux Python image
FROM python:3.11-slim

# Install the Java Virtual Machine required for Spark
RUN apt-get update && \
    apt-get install -y default-jre && \
    rm -rf /var/lib/apt/lists/*

# Install PySpark
RUN pip install pyspark==3.5.1

# Copy our code into the Container
WORKDIR /app
COPY streaming_consumer.py .

# Run the PySpark streaming job
CMD ["python", "streaming_consumer.py"]
