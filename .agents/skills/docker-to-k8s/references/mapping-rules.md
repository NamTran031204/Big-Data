# Component Mapping Reference

This file documents the standard mapping between Docker/source-code components
and their Kubernetes equivalents. The skill consults this during Step 3.

## Docker Compose → K8s Mapping

### docker-compose.yml Fields

| Docker Compose | Kubernetes Equivalent | Example |
|---|---|---|
| `image:` | `spec.containers[].image` | `postgres:16` |
| `container_name:` | `metadata.name` (pod name via Deployment) | `bigdata-postgres` |
| `ports: "5432:5432"` | Service `port`/`targetPort` + `containerPort` | `5432` |
| `environment:` | `env:` or `envFrom: secretRef/configMapRef` | |
| `volumes:` (named) | `PersistentVolumeClaim` + `volumeMounts` | |
| `volumes:` (bind mount) | `ConfigMap` or `hostPath` (dev only) | `./scripts:/scripts:ro` |
| `depends_on:` | `initContainers` + wait scripts or `readinessProbe` | |
| `networks:` | Not needed (all pods share namespace DNS) | |
| `restart: unless-stopped` | `restartPolicy: Always` (Deployment default) | |
| `healthcheck:` | `readinessProbe` + `livenessProbe` | |
| `deploy.resources.limits` | `resources.limits` | `cpu: "2"`, `memory: 4Gi` |
| `deploy.resources.reservations` | `resources.requests` | `cpu: "500m"`, `memory: 512Mi` |
| `command:` | `command:` + `args:` | |

### Service Type Decisions

| Access Pattern | K8s Service Type | When to Use |
|---|---|---|
| Internal only (pod-to-pod) | `ClusterIP` | Databases, Kafka, internal APIs |
| Developer UI access | `NodePort` | Grafana, Kafka UI, MinIO Console, Airflow |
| External API | `LoadBalancer` or `Ingress` | Production API (not for Minikube local) |

### Workload Type Decisions

| Criteria | Use This | Why |
|---|---|---|
| Stateful + needs stable network | `StatefulSet` | Databases (Postgres, MongoDB, Kafka) |
| Stateless long-running | `Deployment` | API servers, connectors, streaming |
| Run-once then exit | `Job` | Spark batch, data migration |
| Run on schedule | `CronJob` | Periodic batch processing |
| Init tasks (create bucket, etc.) | `initContainer` or `Job` | MinIO bucket init, schema creation |

## Component-Specific Notes

### PostgreSQL
- Use StatefulSet with 1 replica
- Add `command` args for WAL config: `wal_level=logical`, `max_replication_slots=4`
- PVC for `/var/lib/postgresql/data`
- Init SQL can be mounted via ConfigMap to `/docker-entrypoint-initdb.d/`

### Kafka + Zookeeper
- Both are StatefulSets
- Zookeeper: 1 replica, port 2181
- Kafka: 1 replica, internal listener on 29092, advertised listeners must use K8s service names
- PVC for `/var/lib/kafka/data` and `/var/lib/zookeeper/data`
- `KAFKA_ADVERTISED_LISTENERS` must reference K8s Service name, not `localhost`

### MongoDB
- StatefulSet with 1 replica
- PVC for `/data/db`
- Init database and root credentials via environment

### MinIO
- Deployment (single instance for dev)
- PVC for `/data`
- healthcheck maps to readinessProbe on `/minio/health/live`
- Console on port 9001 (NodePort for dev access)
- mc init can be an initContainer or a separate Job

### Debezium (Kafka Connect)
- Deployment, 1 replica
- Must reach both Kafka and PostgreSQL services
- REST API on port 8083
- Connector registration is done via curl after pod is ready (not part of YAML)
- Custom image if S3 Sink plugin needed

### Spark
- Streaming: Deployment with `restartPolicy: Always`
- Batch: Job (triggered manually or by Airflow)
- Both need ServiceAccount with RBAC to create executor pods
- Checkpoint location on MinIO for streaming fault tolerance
- Base image: `bitnami/spark:3.5` or custom with project dependencies

### Airflow
- Deployment for scheduler + webserver (or use official Helm chart)
- Needs DB (can share PostgreSQL or use embedded SQLite for dev)
- DAGs mounted via ConfigMap or PVC
- webserver on port 8080 (NodePort)

### Prometheus
- Deployment, 1 replica
- ConfigMap for `prometheus.yml` with scrape targets
- PVC optional for data retention
- Port 9090

### Grafana
- Deployment, 1 replica
- Port 3000 (NodePort for dev access)
- Datasources: Prometheus (metrics), MongoDB (business data)
- Dashboards can be provisioned via ConfigMap

### Spring Boot Java Service
- Deployment, 1-3 replicas
- Build image from Dockerfile in SpringBoot/ directory
- `minikube image build` or `eval $(minikube docker-env)` to build locally
- Application config via ConfigMap / Secret
