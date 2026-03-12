from __future__ import annotations

from datetime import datetime, timedelta
import os

from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator, BranchPythonOperator
from airflow.exceptions import AirflowException


# ----------------------------
# Configuration
# ----------------------------
DATA_DIR = "/opt/airflow/data"
RAW_DATA_PATH = f"{DATA_DIR}/Titanic-Dataset.csv"
PROCESSED_DIR = f"{DATA_DIR}/processed"
MLFLOW_TRACKING_URI = "http://host.docker.internal:5000"
MLFLOW_EXPERIMENT_NAME = "Titanic_Airflow_MLflow_Assignment"
REGISTERED_MODEL_NAME = "TitanicSurvivalModel"

os.makedirs(PROCESSED_DIR, exist_ok=True)


# Task 2 - Data Ingestion
def data_ingestion(**context):
    import pandas as pd

    if not os.path.exists(RAW_DATA_PATH):
        raise FileNotFoundError(f"Titanic dataset not found at: {RAW_DATA_PATH}")

    df = pd.read_csv(RAW_DATA_PATH)

    print("\n===== DATA INGESTION =====")
    print(f"Dataset path: {RAW_DATA_PATH}")
    print(f"Dataset shape: {df.shape}")
    print("\nMissing values count:")
    print(df.isnull().sum())

    # Push dataset path using XCom
    context["ti"].xcom_push(key="dataset_path", value=RAW_DATA_PATH)


# Task 3 - Data Validation
def data_validation(**context):
    import pandas as pd

    ti = context["ti"]
    dag_run = context.get("dag_run")

    dataset_path = ti.xcom_pull(task_ids="data_ingestion", key="dataset_path")
    if not dataset_path:
        raise AirflowException("Dataset path not found in XCom.")

    # Intentional first-attempt failure to demonstrate retry behavior
    # This will fail on try 1 and pass on retry.
    force_retry_demo = True
    if dag_run and dag_run.conf:
        force_retry_demo = dag_run.conf.get("force_retry_demo", True)

    if force_retry_demo and ti.try_number == 1:
        raise AirflowException("Intentional validation failure on first try to demonstrate retry behavior.")

    df = pd.read_csv(dataset_path)

    age_missing_pct = df["Age"].isnull().mean() * 100
    embarked_missing_pct = df["Embarked"].isnull().mean() * 100

    print("\n===== DATA VALIDATION =====")
    print(f"Age missing percentage: {age_missing_pct:.2f}%")
    print(f"Embarked missing percentage: {embarked_missing_pct:.2f}%")

    if age_missing_pct > 30:
        raise AirflowException(f"Validation failed: Age missing percentage is {age_missing_pct:.2f}% (> 30%).")

    if embarked_missing_pct > 30:
        raise AirflowException(f"Validation failed: Embarked missing percentage is {embarked_missing_pct:.2f}% (> 30%).")

    print("Validation passed.")



# Task 4A - Handle Missing Values
def handle_missing_values(**context):
    import pandas as pd

    ti = context["ti"]
    dataset_path = ti.xcom_pull(task_ids="data_ingestion", key="dataset_path")

    df = pd.read_csv(dataset_path)

    print("\n===== HANDLE MISSING VALUES =====")

    # Fill Age with median
    df["Age"] = df["Age"].fillna(df["Age"].median())

    # Fill Embarked with mode
    if df["Embarked"].mode().empty:
        df["Embarked"] = df["Embarked"].fillna("S")
    else:
        df["Embarked"] = df["Embarked"].fillna(df["Embarked"].mode()[0])

    missing_output_path = f"{PROCESSED_DIR}/missing_handled.csv"
    df.to_csv(missing_output_path, index=False)

    print(f"Saved missing-value-handled dataset to: {missing_output_path}")
    ti.xcom_push(key="missing_handled_path", value=missing_output_path)


# Task 4B - Feature Engineering
def feature_engineering(**context):
    import pandas as pd

    ti = context["ti"]
    dataset_path = ti.xcom_pull(task_ids="data_ingestion", key="dataset_path")

    df = pd.read_csv(dataset_path)

    print("\n===== FEATURE ENGINEERING =====")

    # Create engineered features
    df["FamilySize"] = df["SibSp"] + df["Parch"] + 1
    df["IsAlone"] = (df["FamilySize"] == 1).astype(int)

    # Keep only the merge key + engineered columns
    engineered_df = df[["PassengerId", "FamilySize", "IsAlone"]].copy()

    features_output_path = f"{PROCESSED_DIR}/engineered_features.csv"
    engineered_df.to_csv(features_output_path, index=False)

    print(f"Saved engineered features to: {features_output_path}")
    ti.xcom_push(key="engineered_features_path", value=features_output_path)


# Task 5 - Data Encoding
def encode_data(**context):
    import pandas as pd

    ti = context["ti"]

    missing_handled_path = ti.xcom_pull(task_ids="handle_missing_values", key="missing_handled_path")
    engineered_features_path = ti.xcom_pull(task_ids="feature_engineering", key="engineered_features_path")

    df_main = pd.read_csv(missing_handled_path)
    df_features = pd.read_csv(engineered_features_path)

    print("\n===== DATA ENCODING =====")

    # Merge engineered features back
    df = df_main.merge(df_features, on="PassengerId", how="left")

    # Encode categorical columns
    df["Sex"] = df["Sex"].map({"male": 0, "female": 1})

    embarked_dummies = pd.get_dummies(df["Embarked"], prefix="Embarked")
    df = pd.concat([df, embarked_dummies], axis=1)

    # Drop irrelevant columns
    columns_to_drop = ["Name", "Ticket", "Cabin", "Embarked"]
    existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
    df = df.drop(columns=existing_columns_to_drop)

    # Optionally drop PassengerId as a non-predictive identifier
    if "PassengerId" in df.columns:
        df = df.drop(columns=["PassengerId"])

    encoded_output_path = f"{PROCESSED_DIR}/encoded_data.csv"
    df.to_csv(encoded_output_path, index=False)

    print(f"Saved encoded dataset to: {encoded_output_path}")
    print(f"Encoded dataset shape: {df.shape}")
    ti.xcom_push(key="encoded_data_path", value=encoded_output_path)


# Task 6 - Model Training with MLflow
def train_model(**context):
    import pandas as pd
    import mlflow
    import mlflow.sklearn
    from sklearn.model_selection import train_test_split
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier

    ti = context["ti"]
    dag_run = context.get("dag_run")

    encoded_data_path = ti.xcom_pull(task_ids="encode_data", key="encoded_data_path")
    if not encoded_data_path:
        raise AirflowException("Encoded data path not found in XCom.")

    df = pd.read_csv(encoded_data_path)

    # Separate features and target
    if "Survived" not in df.columns:
        raise AirflowException("Target column 'Survived' not found in dataset.")

    X = df.drop(columns=["Survived"])
    y = df["Survived"]

    # Fill any remaining missing values defensively
    X = X.fillna(0)

    # Read hyperparameters from DAG run config if provided
    conf = dag_run.conf if dag_run and dag_run.conf else {}
    model_type = conf.get("model_type", "logistic_regression")
    test_size = float(conf.get("test_size", 0.2))
    random_state = int(conf.get("random_state", 42))
    
    max_iter = int(conf.get("max_iter", 1000))
    c_value = float(conf.get("c_value", 0.5))
    solver = conf.get("solver", "liblinear")
    
    n_estimators = int(conf.get("n_estimators", 200))
    max_depth = conf.get("max_depth", 8)
    max_depth = None if max_depth in ("None", None) else int(max_depth)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y
    )

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    print("\n===== MODEL TRAINING =====")
    print(f"Tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"Experiment: {MLFLOW_EXPERIMENT_NAME}")
    print(f"Model type: {model_type}")

    with mlflow.start_run(run_name=f"{model_type}_run") as run:
        run_id = run.info.run_id

        if model_type == "logistic_regression":
            model = LogisticRegression(
                max_iter=max_iter,
                C=c_value,
                solver=solver,
                random_state=random_state
            )
            mlflow.log_param("model_type", "LogisticRegression")
            mlflow.log_param("max_iter", max_iter)
            mlflow.log_param("C", c_value)
            mlflow.log_param("solver", solver)
            mlflow.log_param("random_state", random_state)
            
        elif model_type == "random_forest":
            model = RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=random_state
            )
            mlflow.log_param("model_type", "RandomForestClassifier")
            mlflow.log_param("n_estimators", n_estimators)
            mlflow.log_param("max_depth", max_depth)
            mlflow.log_param("random_state", random_state)

        else:
            raise AirflowException("Invalid model_type. Use 'logistic_regression' or 'random_forest'.")

        mlflow.log_param("dataset_size", len(df))
        mlflow.log_param("feature_count", X.shape[1])
        mlflow.log_param("test_size", test_size)

        model.fit(X_train, y_train)

        # Log model artifact
        mlflow.sklearn.log_model(model, artifact_path="model")

        # Save split data for next task
        X_test_path = f"{PROCESSED_DIR}/X_test.csv"
        y_test_path = f"{PROCESSED_DIR}/y_test.csv"

        X_test.to_csv(X_test_path, index=False)
        y_test.to_csv(y_test_path, index=False)

        # Save model locally too
        local_model_path = f"{PROCESSED_DIR}/trained_model.pkl"
        import joblib
        joblib.dump(model, local_model_path)

        ti.xcom_push(key="run_id", value=run_id)
        ti.xcom_push(key="local_model_path", value=local_model_path)
        ti.xcom_push(key="X_test_path", value=X_test_path)
        ti.xcom_push(key="y_test_path", value=y_test_path)

        print(f"Run ID: {run_id}")
        print(f"Local model path: {local_model_path}")


# Task 7 - Model Evaluation
def evaluate_model(**context):
    import pandas as pd
    import joblib
    import mlflow
    from mlflow.tracking import MlflowClient
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

    ti = context["ti"]

    run_id = ti.xcom_pull(task_ids="train_model", key="run_id")
    local_model_path = ti.xcom_pull(task_ids="train_model", key="local_model_path")
    X_test_path = ti.xcom_pull(task_ids="train_model", key="X_test_path")
    y_test_path = ti.xcom_pull(task_ids="train_model", key="y_test_path")

    if not all([run_id, local_model_path, X_test_path, y_test_path]):
        raise AirflowException("Missing XCom values needed for evaluation.")

    model = joblib.load(local_model_path)
    X_test = pd.read_csv(X_test_path)
    y_test = pd.read_csv(y_test_path).squeeze("columns")

    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(y_test, predictions, zero_division=0)
    recall = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)

    print("\n===== MODEL EVALUATION =====")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-score:  {f1:.4f}")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)

    client.log_metric(run_id, "accuracy", float(accuracy))
    client.log_metric(run_id, "precision", float(precision))
    client.log_metric(run_id, "recall", float(recall))
    client.log_metric(run_id, "f1_score", float(f1))

    ti.xcom_push(key="accuracy", value=float(accuracy))
    ti.xcom_push(key="run_id", value=run_id)


# Task 8 - Branching Logic
def branch_on_accuracy(**context):
    ti = context["ti"]
    accuracy = ti.xcom_pull(task_ids="evaluate_model", key="accuracy")

    print("\n===== BRANCH DECISION =====")
    print(f"Accuracy received: {accuracy}")

    if accuracy >= 0.80:
        print("Accuracy >= 0.80 -> register_model")
        return "register_model"
    else:
        print("Accuracy < 0.80 -> reject_model")
        return "reject_model"


# Task 9A - Register Model
def register_model(**context):
    import mlflow
    from mlflow.tracking import MlflowClient

    ti = context["ti"]
    run_id = ti.xcom_pull(task_ids="evaluate_model", key="run_id")

    if not run_id:
        raise AirflowException("Run ID not found for model registration.")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)

    # Create registered model if it doesn't exist
    try:
        client.create_registered_model(REGISTERED_MODEL_NAME)
        print(f"Created registered model: {REGISTERED_MODEL_NAME}")
    except Exception:
        print(f"Registered model '{REGISTERED_MODEL_NAME}' already exists or could not be created. Continuing...")

    model_uri = f"runs:/{run_id}/model"
    result = mlflow.register_model(model_uri=model_uri, name=REGISTERED_MODEL_NAME)

    client.set_tag(run_id, "model_status", "registered")
    client.set_tag(run_id, "registered_model_name", REGISTERED_MODEL_NAME)

    print("\n===== MODEL REGISTRATION =====")
    print(f"Registered model URI: {model_uri}")
    print(f"Model version: {result.version}")


# Task 9B - Reject Model
def reject_model(**context):
    import mlflow
    from mlflow.tracking import MlflowClient

    ti = context["ti"]
    run_id = ti.xcom_pull(task_ids="evaluate_model", key="run_id")
    accuracy = ti.xcom_pull(task_ids="evaluate_model", key="accuracy")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)

    if run_id:
        client.set_tag(run_id, "model_status", "rejected")
        client.set_tag(run_id, "rejection_reason", f"Accuracy below threshold: {accuracy:.4f} < 0.80")

    print("\n===== MODEL REJECTION =====")
    print(f"Model rejected because accuracy {accuracy:.4f} < 0.80")


# DAG Definition
with DAG(
    dag_id="mlops_airflow_mlflow_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["assignment", "mlops", "titanic", "mlflow"],
    default_args={
        "owner": "hejab",
        "retries": 0,
    },
    description="End-to-end Titanic survival ML pipeline using Airflow and MLflow.",
) as dag:

    task_ingestion = PythonOperator(
        task_id="data_ingestion",
        python_callable=data_ingestion,
    )

    task_validation = PythonOperator(
        task_id="data_validation",
        python_callable=data_validation,
        retries=1,  # Intentional failure on first try, success on retry
        retry_delay=timedelta(minutes=1),
    )

    task_missing = PythonOperator(
        task_id="handle_missing_values",
        python_callable=handle_missing_values,
    )

    task_features = PythonOperator(
        task_id="feature_engineering",
        python_callable=feature_engineering,
    )

    task_encoding = PythonOperator(
        task_id="encode_data",
        python_callable=encode_data,
    )

    task_training = PythonOperator(
        task_id="train_model",
        python_callable=train_model,
    )

    task_evaluation = PythonOperator(
        task_id="evaluate_model",
        python_callable=evaluate_model,
    )

    task_branch = BranchPythonOperator(
        task_id="branch_on_accuracy",
        python_callable=branch_on_accuracy,
    )

    task_register = PythonOperator(
        task_id="register_model",
        python_callable=register_model,
    )

    task_reject = PythonOperator(
        task_id="reject_model",
        python_callable=reject_model,
    )

    # No cyclic dependencies
    # Validation -> parallel tasks -> encoding -> training -> evaluation -> branching
    task_ingestion >> task_validation
    task_validation >> [task_missing, task_features]
    [task_missing, task_features] >> task_encoding
    task_encoding >> task_training >> task_evaluation >> task_branch
    task_branch >> task_register
    task_branch >> task_reject