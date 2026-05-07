---
name: docker-to-k8s
description: Automatically map Docker images and service source code to Kubernetes (K8s) manifest files targeting Minikube. Use this skill whenever the user wants to generate K8s YAML from docker-compose, convert Docker services to Kubernetes deployments, scaffold a k8s/ directory from an existing project, deploy containers to Minikube, or synchronize infrastructure changes between Docker and Kubernetes. Also triggers when the user mentions "deploy to k8s", "create k8s manifests", "minikube setup", "docker to kubernetes", or "map services to k8s".
---

# Docker-to-K8s Mapper

This skill automates the mapping of Docker images, docker-compose services, and application source code into Kubernetes manifest files for local Minikube deployment. It uses a deterministic Python script for environment variable extraction and supports incremental updates via git diff — so only changed components get re-mapped on subsequent runs.

## When to Use

- The user has a Docker-based project and wants to deploy it to Minikube
- The user asks to generate K8s YAML from docker-compose or a project structure
- The user wants to update K8s manifests after making source code or config changes

## Execution Flow

Follow these 5 steps in strict sequential order. Do not skip steps, and do not reorder them.

### Step 1: Prerequisite Check — Minikube

Before doing anything else, verify that `minikube` is installed on the user's machine:

```bash
minikube version
```

If the command fails or `minikube` is not found, **stop entirely** and print:

```
⛔ Minikube is not installed.

To install on Windows:
  1. Download from: https://minikube.sigs.k8s.io/docs/start/
  2. Or via winget:  winget install Kubernetes.minikube
  3. Or via choco:   choco install minikube
  4. Restart your terminal after installation.

Prerequisite: Docker Desktop must be running.
After installing, run: minikube start --driver=docker
```

Do not proceed to Step 2 until minikube is confirmed available.

### Step 2: Delta Execution via Git

The goal is to avoid re-generating everything on every run. We track the last processed commit in `references/git.md` (located inside this skill's directory).

1. **Read** `references/git.md` from this skill's directory.
2. **If the file has content** (a commit hash):
   - Run `git log --oneline -1` to get the current HEAD commit hash.
   - Run `git diff <saved_hash> HEAD --name-only` to get list of changed files.
   - Filter the changed files to identify which components are affected (see mapping table in Step 3).
   - Only process the affected components.
   - After processing, update `references/git.md` with the new HEAD commit hash.
3. **If the file is empty or doesn't exist** (first run):
   - Proceed to Step 3 (full directory scan).
   - After processing, write the current HEAD commit hash to `references/git.md`.

### Step 3: Directory Scanning & Component Mapping

Scan the project root and the `init/` directory. Map each recognized directory/service to a K8s component:

| Source Directory / Docker Service | K8s Component Name | K8s Workload Type | Notes |
|---|---|---|---|
| `init/docker-compose.yml` → `postgres` service | `infrastructure/postgres/` | StatefulSet | Needs PVC, WAL config |
| `init/docker-compose.yml` → `kafka` + `zookeeper` | `infrastructure/kafka/` | StatefulSet | Both zk and broker |
| `init/docker-compose.yml` → `mongodb` | `infrastructure/mongodb/` | StatefulSet | Needs PVC |
| `init/docker-compose.yml` → `minio` | `infrastructure/minio/` | Deployment | healthcheck → readinessProbe |
| `init/docker-compose.yml` → `debezium-connect` | `pipeline/debezium/` | Deployment | Needs both networks |
| `services/spark-streaming/` | `pipeline/spark/` | Deployment | Runs 24/7, restartPolicy Always |
| Spark batch scripts | `pipeline/spark/` | Job | Triggered by Airflow |
| `SpringBoot/` | `services/java-service/` | Deployment | Spring Boot API |
| Airflow (if present) | `pipeline/airflow/` | Deployment | Scheduler + webserver |
| Prometheus (if present) | `monitoring/prometheus/` | Deployment | Scrape configs via ConfigMap |
| Grafana (if present) | `monitoring/grafana/` | Deployment | Dashboards |

For each component, generate the following files inside `k8s/<component-path>/`:
- `deployment.yaml` (or `statefulset.yaml` for stateful services)
- `service.yaml` (ClusterIP for internal, NodePort for UI-exposed)
- `pvc.yaml` (if stateful)

Additionally generate these shared files:
- `k8s/namespace.yaml` — namespace `bigdata`
- `k8s/configmaps/` — non-sensitive configuration
- `k8s/storage/` — PersistentVolumeClaim files

### Step 4: Environment Variable Mapping via Python Script

Run the Python script at `scripts/map_env.py` (located inside this skill's directory) to parse the project's `.env` file and generate K8s Secrets and ConfigMaps.

The `.env` file uses **flag comments** to group variables by component:

```env
# Flag format: #<component-name>
#postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

#minio
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=admin123456

#mongodb
MONGO_USER=admin
MONGO_PASSWORD=admin123456
```

Execute the script:

```bash
python <skill-dir>/scripts/map_env.py --env-file <project-root>/init/.env --output-dir <project-root>/k8s/secrets/
```

The script will:
1. Parse the `.env` file, grouping variables by their flag comment
2. For each component group, create a K8s Secret YAML file: `<component>-secret.yaml`
3. Separate sensitive values (passwords, keys) into Secrets and non-sensitive values into ConfigMaps

After the script runs, read its stdout to confirm which files were generated.

### Step 5: Deployment Guide (`deploy-local.md`)

**First run** (when `references/git.md` was empty): Create `k8s/deploy-local.md` with the full deployment guide. Read the template from `references/deploy-template.md` in this skill's directory and customize it for the specific components discovered in Step 3.

**Subsequent runs**: Only update `k8s/deploy-local.md` if the changes detected in Step 2 require new deployment steps (e.g., a new service was added, a port changed, a new PVC is needed).

## K8s Manifest Generation Rules

When generating YAML manifests, follow these conventions:

### Networking
- All resources go in namespace `bigdata`
- Internal services use `ClusterIP` (e.g., postgres, kafka, mongodb)
- UI services use `NodePort` (e.g., grafana:3000, kafka-ui:8080, airflow:8080, minio-console:9001, spark-ui:4040)
- Service DNS: `<service-name>.bigdata.svc.cluster.local` (or just `<service-name>` within the namespace)

### Docker-to-K8s translation
- `depends_on` → use `initContainers` with wait scripts or `readinessProbe`
- `volumes` → `PersistentVolumeClaim` (stateful) or `emptyDir` (ephemeral)
- `environment` → `envFrom: secretRef` / `configMapRef`
- `ports` → `containerPort` in pod + `port`/`targetPort` in Service
- `networks` → not needed in K8s (all pods can communicate within namespace)
- `healthcheck` → `readinessProbe` + `livenessProbe`
- `restart: unless-stopped` → `restartPolicy: Always` (default in Deployment)
- `deploy.resources` → `resources.requests` and `resources.limits`

### Spark-specific
- Spark needs a `ServiceAccount` with RBAC to create/delete executor Pods
- Spark Streaming → `Deployment` (long-running, `restartPolicy: Always`)
- Spark Batch → `Job` or `CronJob` (ephemeral, triggered by Airflow)
- Both share the same base image, differentiated by the main Python script

### Labels convention
```yaml
labels:
  app: <service-name>
  tier: infrastructure | pipeline | monitoring | services
  part-of: bigdata
```
