FROM apache/airflow:2.9.0-python3.11

USER root

# Java (Spark 실행에 필요)
RUN apt-get update && \
    apt-get install -y --no-install-recommends openjdk-17-jre-headless curl && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# GCS Connector JAR
ARG GCS_CONNECTOR_VERSION=2.2.5
RUN mkdir -p /opt/gcs-jars && \
    curl -fL -o /opt/gcs-jars/gcs-connector-hadoop3-shaded.jar \
    https://repo1.maven.org/maven2/com/google/cloud/bigdataoss/gcs-connector/hadoop3-${GCS_CONNECTOR_VERSION}/gcs-connector-hadoop3-${GCS_CONNECTOR_VERSION}-shaded.jar && \
    chmod 644 /opt/gcs-jars/gcs-connector-hadoop3-shaded.jar

USER airflow

# Python 패키지 설치 (pyspark에 spark-submit 포함)
RUN pip install --no-cache-dir \
    apache-airflow-providers-apache-spark==4.7.1 \
    pyspark==3.5.0 \
    kaggle \
    google-cloud-storage==2.16.0

RUN pip install --no-cache-dir dbt-bigquery==1.8.2

# SparkSubmitOperator가 참조하는 SPARK_HOME
ENV SPARK_HOME=/home/airflow/.local/lib/python3.11/site-packages/pyspark
ENV PATH=$PATH:$SPARK_HOME/bin
ENV PYSPARK_PYTHON=python3
