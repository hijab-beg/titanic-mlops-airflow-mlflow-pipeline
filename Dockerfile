FROM apache/airflow:3.1.7

USER airflow

RUN pip install --no-cache-dir \
    "pandas==2.2.3" \
    "numpy==2.1.3" \
    "scikit-learn==1.5.2" \
    "joblib==1.4.2" \
    "mlflow==3.10.1"