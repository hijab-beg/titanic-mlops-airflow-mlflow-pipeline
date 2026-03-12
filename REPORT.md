# Technical Report: Airflow + MLflow Titanic Survival Pipeline


## 1. Architecture Explanation (Airflow + MLflow Interaction)

This project implements an end-to-end machine learning pipeline for predicting Titanic passenger survival using **Apache Airflow** for orchestration and **MLflow** for experiment tracking and model management.

The architecture integrates data processing, model training, evaluation, and model registry into a reproducible workflow.

### Airflow as Pipeline Orchestrator

Airflow acts as the pipeline orchestrator, coordinating the sequence of tasks required to transform the raw dataset into a trained machine learning model. Each stage of the pipeline is implemented as a separate Airflow task using `PythonOperator`.

### MLflow for Experiment Tracking

MLflow is used for experiment tracking and model lifecycle management. During the model training stage, the pipeline logs:

- **Hyperparameters**
- **Dataset characteristics**
- **Trained model artifacts**
- **Evaluation metrics**

These are stored in the MLflow tracking server under the experiment:

```
Titanic_Airflow_MLflow_Assignment
```

The Airflow container communicates with the MLflow tracking server through:

```
http://host.docker.internal:5000
```

### Model Registration Logic

After model evaluation, the pipeline applies branching logic to determine whether the trained model should be registered in the MLflow Model Registry.

If the model meets the performance threshold, it is registered as a new version of the model.

### Integrated Architecture

This architecture integrates:

- Workflow orchestration
- Experiment tracking
- Model lifecycle management

into a production-style machine learning pipeline.

---

## 2. DAG Structure and Dependency Explanation

The pipeline is implemented as a **Directed Acyclic Graph (DAG)**.

The DAG contains sequential tasks representing the machine learning workflow.

### 1. Data Ingestion

The pipeline begins with the `data_ingestion` task.

This task:
- Loads the Titanic dataset
- Verifies that the dataset exists
- Prints dataset statistics

Examples of printed information:
- Dataset shape
- Missing values

The dataset path is passed to downstream tasks using Airflow **XCom**.

### 2. Data Validation

The `data_validation` task performs integrity checks.

It calculates the missing value percentage for:
- Age
- Embarked

If the missing value percentage exceeds a threshold, the pipeline raises an exception.

An intentional failure is implemented on the first attempt to demonstrate Airflow retry behavior.

### 3. Data Preprocessing

After validation, two tasks run **in parallel**:

#### Handle Missing Values
- **Age** → replaced with median
- **Embarked** → replaced with mode

#### Feature Engineering
Two new features are created:
- `FamilySize`
- `IsAlone`

These features capture passenger family relationships.

### 4. Data Encoding

The `encode_data` task prepares the dataset for machine learning.

Operations performed:
- Merge engineered features
- Convert `Sex` column to numeric values
- Apply one-hot encoding to `Embarked`

Irrelevant columns removed:
- Name
- Ticket
- Cabin

### 5. Model Training

The `train_model` task trains a Logistic Regression model using Scikit-learn.

The dataset is split using stratified train/test split.

MLflow logs:
- Hyperparameters
- Dataset statistics
- Trained model artifact

### 6. Model Evaluation

The `evaluate_model` task calculates evaluation metrics:
- **Accuracy**
- **Precision**
- **Recall**
- **F1 Score**

These metrics are logged to MLflow.

### 7. Branching Decision

The `branch_on_accuracy` task determines the next step.

Decision logic:
- If accuracy ≥ 0.80 → **register model**
- If accuracy < 0.80 → **reject model**

### 8. Model Registration or Rejection

Two possible outcomes:

**`register_model`**
- Registers the trained model in MLflow Model Registry

**`reject_model`**
- Marks the run as rejected if performance is below threshold

---

## 3. Experiment Comparison Analysis

Three experiments were conducted using **Logistic Regression**.

### Hyperparameters

| Parameter | Experiment 3 | Experiment 2 | Experiment 1 |
|-----------|--------------|--------------|--------------|
| model_type | LogisticRegression | LogisticRegression | LogisticRegression |
| max_iter | 1000 | 500 | 200 |
| C | 0.5 | default | default |
| solver | liblinear | default | default |
| dataset_size | 891 | 891 | 891 |
| feature_count | 11 | 11 | 11 |
| test_size | 0.2 | 0.2 | 0.2 |
| random_state | 42 | 42 | 42 |

### Evaluation Metrics

| Metric | Experiment 3 | Experiment 2 | Experiment 1 |
|--------|--------------|--------------|--------------|
| **Accuracy** | **0.827** | 0.804 | 0.816 |
| **F1 Score** | **0.756** | 0.729 | 0.740 |
| **Precision** | **0.828** | 0.783 | 0.810 |
| **Recall** | **0.696** | 0.681 | 0.681 |

### Analysis

**Experiment 3** achieved the best performance.

**Reasons:**
- Higher iteration count (`max_iter = 1000`)
- Stronger regularization (`C = 0.5`)
- Use of `liblinear` solver

These settings allowed the model to converge more effectively.

**Experiment 2** showed the lowest performance due to fewer training iterations.

Despite lower performance, Experiment 2 was still registered because the pipeline threshold is:

```
Accuracy ≥ 0.80
```

Experiment 2 achieved:

```
Accuracy = 0.804
```

Therefore it satisfied the registration condition.

---

## 4. Failure and Retry Explanation

The pipeline demonstrates Airflow retry behavior during the validation stage.

The validation code intentionally triggers a failure:

```python
if force_retry_demo and ti.try_number == 1:
    raise AirflowException("Intentional validation failure...")
```

This simulates temporary failures commonly encountered in production systems.

Airflow is configured to retry once:

```python
retries = 1
retry_delay = timedelta(minutes=1)
```

### Execution Flow

1. **First validation attempt fails**
2. Airflow marks the task as failed
3. Airflow schedules a retry
4. **Second attempt succeeds**
5. Pipeline continues execution

This demonstrates Airflow's automatic recovery mechanism.

---

## 5. Reflection on Production Deployment

If deployed in production, several improvements would be necessary.

### Persistent MLflow Backend

MLflow should use a database backend such as **PostgreSQL** for reliable experiment storage.

### Improved Model Selection

Instead of registering any model above a threshold, the pipeline should compare models and promote the best performing version.

### Monitoring

Production systems require:
- Data drift detection
- Model performance monitoring

### Container Orchestration

Tools such as **Kubernetes** could manage Airflow deployments and allow pipelines to scale.

### CI/CD Integration

Continuous integration pipelines could automate:
- Model testing
- Version control
- Deployment

---

## Conclusion

This project successfully demonstrates an integrated MLOps pipeline combining:
- **Apache Airflow** for workflow orchestration
- **MLflow** for experiment tracking and model registry
- **Docker** for containerization

The pipeline implements industry best practices including:
- Modular task design
- Automatic retry mechanisms
- Conditional model registration
- Comprehensive experiment tracking

With the proposed production enhancements, this architecture could serve as a foundation for deploying machine learning models at scale.
