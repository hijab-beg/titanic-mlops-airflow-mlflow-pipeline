# MLOps Pipeline with Airflow and MLflow

An end-to-end MLOps pipeline for Titanic dataset survival prediction using Apache Airflow for workflow orchestration and MLflow for experiment tracking and model registry management.

## 🚀 Project Overview

This project demonstrates a production-ready MLOps pipeline that includes:
- **Data Ingestion**: Loading and initial data exploration
- **Data Validation**: Quality checks with retry logic
- **Data Preprocessing**: Missing value handling and feature engineering
- **Data Encoding**: Categorical variable transformation
- **Model Training**: Support for Logistic Regression and Random Forest
- **Model Evaluation**: Comprehensive metrics tracking
- **Model Registration**: Conditional model versioning based on accuracy thresholds

## 📋 Architecture

```
┌─────────────┐
│  Airflow    │ ──── Orchestrates ML Pipeline
│  (Docker)   │
└──────┬──────┘
       │
       ├─── Data Pipeline Tasks
       │    ├── Ingestion
       │    ├── Validation (with retry)
       │    ├── Missing Values Handling
       │    ├── Feature Engineering
       │    └── Encoding
       │
       └─── ML Pipeline Tasks
            ├── Train Model
            ├── Evaluate Model
            ├── Branch on Accuracy
            └── Register Model (if accuracy > threshold)
                 │
                 └──> MLflow Server
```

## 🛠️ Technology Stack

- **Apache Airflow 3.1.7**: Workflow orchestration
- **MLflow 3.10.1**: Experiment tracking and model registry
- **Docker & Docker Compose**: Containerization
- **PostgreSQL**: Airflow metadata database
- **Redis**: Celery task queue
- **Python 3.x**: Core programming language
- **scikit-learn 1.5.2**: Machine learning library
- **Pandas 2.2.3**: Data manipulation

## 📁 Project Structure

```
.
├── dags/
│   └── pipeline.py              # Main Airflow DAG definition
├── data/
│   ├── Titanic-Dataset.csv      # Raw dataset
│   └── processed/               # Processed datasets and models
├── config/
│   └── airflow.cfg              # Airflow configuration
├── plugins/                     # Custom Airflow plugins (if any)
├── logs/                        # Airflow task logs
├── mlartifacts/                 # MLflow artifacts storage
├── mlflow-env/                  # Python virtual environment for MLflow
├── docker-compose.yaml          # Docker Compose configuration
├── Dockerfile                   # Custom Airflow image
└── requirements.txt             # Python dependencies
```

## 🔧 Prerequisites

- Docker Desktop installed and running
- Python 3.x (for MLflow server)
- Git (for version control)
- At least 4GB RAM allocated to Docker

## 📦 Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Start Airflow with Docker Compose

```bash
# Start all services in detached mode
docker compose up -d

# Check running containers
docker ps

# View logs for specific container
docker logs <container_name>
```

**Default Airflow Web UI**: http://localhost:8080
- Username: `airflow`
- Password: `airflow`

### 3. Start MLflow Tracking Server

Open a new terminal and activate the virtual environment:

```bash
# Activate virtual environment (Windows)
.\mlflow-env\Scripts\Activate.ps1

# Start MLflow server
mlflow server --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5000 --workers 1 --disable-security-middleware
```

**MLflow UI**: http://localhost:5000

## 🎯 Usage

### Running the Pipeline

1. Navigate to Airflow UI at http://localhost:8080
2. Locate the DAG: `mlops_airflow_mlflow_pipeline`
3. Enable the DAG by toggling the switch
4. Trigger the DAG manually or wait for scheduled run

### Configuring Model Parameters

You can pass custom parameters when triggering the DAG:

```json
{
  "model_type": "random_forest",
  "n_estimators": 200,
  "max_depth": 8,
  "test_size": 0.2,
  "random_state": 42
}
```

**Supported Model Types:**
- `logistic_regression` (default)
- `random_forest`

**Logistic Regression Parameters:**
- `max_iter`: Maximum iterations (default: 1000)
- `c_value`: Regularization strength (default: 0.5)
- `solver`: Algorithm solver (default: "liblinear")

**Random Forest Parameters:**
- `n_estimators`: Number of trees (default: 200)
- `max_depth`: Maximum tree depth (default: 8)

### Viewing Results

1. **Airflow**: Monitor task execution, logs, and XCom data
2. **MLflow**: Track experiments, compare runs, and view registered models
   - Navigate to http://localhost:5000
   - Select experiment: `Titanic_Airflow_MLflow_Assignment`
   - Compare metrics, parameters, and artifacts

## 🔄 Pipeline Tasks

| Task | Description | Retry Logic |
|------|-------------|-------------|
| `data_ingestion` | Load Titanic dataset | - |
| `data_validation` | Validate data quality | ✅ Retries on failure |
| `handle_missing_values` | Impute missing Age & Embarked | - |
| `feature_engineering` | Create FamilySize & IsAlone features | - |
| `encode_data` | Encode categorical variables | - |
| `train_model` | Train ML model & log to MLflow | - |
| `evaluate_model` | Calculate metrics & log to MLflow | - |
| `branch_on_accuracy` | Branch based on accuracy threshold | - |
| `register_model` | Register model if accuracy > 0.75 | Conditional |

## 📊 Model Metrics

The pipeline tracks the following metrics:
- **Accuracy**
- **Precision**
- **Recall**
- **F1 Score**

Models are automatically registered in MLflow Model Registry if accuracy exceeds 75%.

## 🐳 Docker Commands Reference

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View all running containers
docker ps

# View logs for specific container
docker logs <container_name>

# Follow logs in real-time
docker logs -f <container_name>

# Access container shell
docker exec -it <container_name> bash

# Rebuild images after Dockerfile changes
docker compose build

# Remove all containers and volumes
docker compose down -v
```

## 🧪 MLflow Commands Reference

```bash
# Start MLflow server
mlflow server --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5000 --workers 1 --disable-security-middleware

# Start with different backend (PostgreSQL example)
mlflow server --backend-store-uri postgresql://user:password@localhost/mlflow --host 0.0.0.0 --port 5000

# UI only mode (no tracking server)
mlflow ui --port 5000
```

## 🚨 Troubleshooting

### Issue: Containers not starting
```bash
# Check Docker daemon is running
docker info

# Check for port conflicts
netstat -ano | findstr :8080
netstat -ano | findstr :5000

# View detailed container logs
docker compose logs
```

### Issue: MLflow cannot connect from Airflow
- Ensure MLflow server is running on host machine
- Verify `MLFLOW_TRACKING_URI` in pipeline.py uses `host.docker.internal:5000`
- Check firewall settings allow connections on port 5000

### Issue: Permission errors in Docker
```bash
# Set AIRFLOW_UID in .env file
echo "AIRFLOW_UID=$(id -u)" > .env
docker compose down -v
docker compose up -d
```

## 📝 Configuration

### Airflow Configuration
Custom configuration is located in `config/airflow.cfg`. Key settings:
- Executor: CeleryExecutor
- Database: PostgreSQL
- Broker: Redis

### MLflow Configuration
- **Tracking URI**: `http://host.docker.internal:5000` (from Docker containers)
- **Experiment Name**: `Titanic_Airflow_MLflow_Assignment`
- **Model Registry**: SQLite backend
- **Artifact Store**: Local file system (`mlartifacts/`)

## 🔐 Environment Variables

Key environment variables in `docker-compose.yaml`:
- `AIRFLOW__CORE__EXECUTOR`: CeleryExecutor
- `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`: PostgreSQL connection
- `AIRFLOW__CELERY__BROKER_URL`: Redis connection
- `AIRFLOW_CONFIG`: Custom config file path

## 📈 Future Enhancements

- [ ] Add data drift detection
- [ ] Implement A/B testing framework
- [ ] Add model performance monitoring
- [ ] Integrate with cloud storage (S3/Azure Blob)
- [ ] Add automated model retraining
- [ ] Implement CI/CD pipeline
- [ ] Add comprehensive unit tests
- [ ] Add data versioning with DVC

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

Hijab Beg

## 🙏 Acknowledgments

- Apache Airflow community
- MLflow project
- Kaggle for the Titanic dataset
- Docker for containerization platform

---

**Note**: This is an educational task demonstrating MLOps best practices with Airflow and MLflow integration.
