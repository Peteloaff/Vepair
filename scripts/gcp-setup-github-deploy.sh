#!/usr/bin/env bash
# One-time setup so GitHub Actions can deploy the API to Cloud Run without any stored key.
# Run it in Google Cloud Shell, in the project that hosts the vepair-api Cloud Run service:
#
#     bash scripts/gcp-setup-github-deploy.sh
#
# It is safe to run again: anything that already exists is left alone. At the end it prints the
# three values to give to GitHub (they are identifiers, not secrets).
#
# What it creates:
#   - a service account "github-deployer" that can deploy to Cloud Run from source
#   - a Workload Identity pool + provider that trust GitHub's identity tokens, but ONLY for
#     repository REPO on the main branch. A fork, a pull request or another branch gets nothing.
set -euo pipefail

REPO="Peteloaff/Vepair"
POOL="github"
PROVIDER="vepair-repo"
SA_NAME="github-deployer"

PROJECT_ID="$(gcloud config get-value project 2>/dev/null)"
if [ -z "$PROJECT_ID" ]; then
  echo "No Google Cloud project is selected. Run: gcloud config set project YOUR_PROJECT_ID" >&2
  exit 1
fi
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
SA="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Project: $PROJECT_ID ($PROJECT_NUMBER)"
echo "Repository trusted: $REPO (main branch only)"
echo

echo "1/5 Enabling the Google APIs the deploy uses..."
gcloud services enable \
  iamcredentials.googleapis.com sts.googleapis.com cloudbuild.googleapis.com \
  run.googleapis.com artifactregistry.googleapis.com iam.googleapis.com

echo "2/5 Service account..."
if ! gcloud iam service-accounts describe "$SA" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" --display-name="GitHub Actions deployer"
fi

echo "3/5 Letting it deploy (Cloud Run, Cloud Build, source upload, run as the service's account)..."
for ROLE in \
  roles/run.admin \
  roles/cloudbuild.builds.editor \
  roles/storage.admin \
  roles/artifactregistry.writer \
  roles/iam.serviceAccountUser \
  roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA}" --role="$ROLE" --condition=None --quiet >/dev/null
done

echo "4/5 Workload Identity pool and provider (trusts only $REPO on main)..."
if ! gcloud iam workload-identity-pools describe "$POOL" --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "$POOL" --location=global --display-name="GitHub"
fi
if ! gcloud iam workload-identity-pools providers describe "$PROVIDER" \
    --location=global --workload-identity-pool="$POOL" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" \
    --location=global --workload-identity-pool="$POOL" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository=='${REPO}' && assertion.ref=='refs/heads/main'"
fi

echo "5/5 Allowing that identity to act as the service account..."
gcloud iam service-accounts add-iam-policy-binding "$SA" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${REPO}" \
  --quiet >/dev/null

echo
echo "Done. Give these three values to GitHub (repository variables, not secrets):"
echo
echo "  GCP_PROJECT_ID                  = ${PROJECT_ID}"
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER  = projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/providers/${PROVIDER}"
echo "  GCP_SERVICE_ACCOUNT             = ${SA}"
echo
