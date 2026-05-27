Write-Host "🛑 Initiating graceful shutdown of VitalPulse infrastructure..." -ForegroundColor Yellow

kubectl delete -f infra/spark-job.yaml --ignore-not-found=true
kubectl delete -f infra/qdrant.yaml --ignore-not-found=true
kubectl delete -f infra/minio.yaml --ignore-not-found=true
kubectl delete -f infra/redpanda.yaml --ignore-not-found=true

Write-Host "🧹 Wiping Persistent Volume Claims to clear disk space..." -ForegroundColor Cyan
kubectl delete pvc --all

Write-Host "✅ Teardown complete. Infrastructure is offline and disk is clean." -ForegroundColor Green