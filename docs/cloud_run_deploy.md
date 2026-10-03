# Cloud Deployment Guide

PulseWatch is designed to be easily deployed to modern cloud providers with minimal cost and zero maintenance.

---

## Option 1: Google Cloud Run + Cloud SQL (Recommended for GCP)

Because PulseWatch includes an asynchronous background alert evaluator that runs on a 60-second periodic cycle, Cloud Run must be configured to keep CPU allocated between incoming HTTP requests.

### 1. Create a Cloud SQL PostgreSQL Instance

```bash
gcloud sql instances create pulsewatch-postgres \
    --database-version=POSTGRES_16 \
    --tier=db-f1-micro \
    --region=us-central1

# Create database and user
gcloud sql databases create pulsewatch --instance=pulsewatch-postgres
gcloud sql users create pulsewatch --instance=pulsewatch-postgres --password=YOUR_STRONG_PASSWORD
```

### 2. Build and Deploy the Backend

```bash
# Submit backend image to Google Artifact Registry
gcloud builds submit backend --tag gcr.io/YOUR_PROJECT_ID/pulsewatch-backend:latest

# Deploy with CPU always allocated and minimum 1 instance for the background worker
gcloud run deploy pulsewatch-api \
    --image gcr.io/YOUR_PROJECT_ID/pulsewatch-backend:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --min-instances 1 \
    --no-cpu-throttling \
    --add-cloudsql-instances YOUR_PROJECT_ID:us-central1:pulsewatch-postgres \
    --set-env-vars "ENVIRONMENT=production,DATABASE_URL=postgresql://pulsewatch:YOUR_STRONG_PASSWORD@/pulsewatch?host=/cloudsql/YOUR_PROJECT_ID:us-central1:pulsewatch-postgres,SECRET_KEY=YOUR_SECURE_RANDOM_KEY"
```

### 3. Deploy the Frontend

```bash
gcloud builds submit frontend --tag gcr.io/YOUR_PROJECT_ID/pulsewatch-frontend:latest

gcloud run deploy pulsewatch-app \
    --image gcr.io/YOUR_PROJECT_ID/pulsewatch-frontend:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

---

## Option 2: Render.com (Lowest Setup Friction)

PulseWatch includes a pre-configured `render.yaml` Blueprint:

1. Push your repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** -> **Blueprint**.
3. Select your repository. Render will automatically provision:
   - **PostgreSQL Database** (`pulsewatch-db`)
   - **Backend Web Service** (`pulsewatch-api` on a standard dyno with continuous process execution)
   - **Frontend Web Service** (`pulsewatch-app`)
4. Click **Apply**. Migrations and deployment run automatically.

---

## Option 3: Railway

1. Install Railway CLI: `npm i -g @railway/cli`
2. Run `railway init` and connect PostgreSQL plugin.
3. Deploy backend: `railway up --service backend`
4. Set environment variables (`DATABASE_URL`, `SECRET_KEY`).
