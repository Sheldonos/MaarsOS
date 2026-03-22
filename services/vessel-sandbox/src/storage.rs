use anyhow::Result;
use aws_config::BehaviorVersion;
use aws_sdk_s3::{
    config::{Credentials, Region},
    primitives::ByteStream,
    Client,
};
use tracing::{debug, info};

pub struct ArtifactStorage {
    client: Client,
    bucket: String,
}

impl ArtifactStorage {
    pub async fn new() -> Self {
        let endpoint_url = std::env::var("MINIO_ENDPOINT")
            .unwrap_or_else(|_| "http://localhost:9000".to_string());
        let access_key = std::env::var("MINIO_ACCESS_KEY").unwrap_or_else(|_| "minioadmin".to_string());
        let secret_key = std::env::var("MINIO_SECRET_KEY").unwrap_or_else(|_| "minioadmin".to_string());
        let bucket = std::env::var("MINIO_BUCKET").unwrap_or_else(|_| "maars-artifacts".to_string());

        info!("Initializing artifact storage with endpoint: {}", endpoint_url);

        // Create S3 client configured for MinIO
        let credentials = Credentials::new(
            access_key,
            secret_key,
            None,
            None,
            "minio-credentials",
        );

        let config = aws_config::defaults(BehaviorVersion::latest())
            .region(Region::new("us-east-1"))
            .credentials_provider(credentials)
            .endpoint_url(endpoint_url)
            .load()
            .await;

        let s3_config = aws_sdk_s3::config::Builder::from(&config)
            .force_path_style(true) // Required for MinIO
            .build();

        let client = Client::from_conf(s3_config);

        Self { client, bucket }
    }

    pub async fn upload_artifact(
        &self,
        task_id: &str,
        filename: &str,
        content: Vec<u8>,
    ) -> Result<String> {
        let key = format!("tasks/{}/{}", task_id, filename);
        
        debug!(
            "Uploading artifact: bucket={}, key={}, size={}",
            self.bucket,
            key,
            content.len()
        );

        let body = ByteStream::from(content);

        self.client
            .put_object()
            .bucket(&self.bucket)
            .key(&key)
            .body(body)
            .send()
            .await?;

        let url = format!(
            "{}/{}/{}",
            std::env::var("MINIO_PUBLIC_URL")
                .unwrap_or_else(|_| "http://localhost:9000".to_string()),
            self.bucket,
            key
        );

        info!("Artifact uploaded successfully: {}", url);

        Ok(url)
    }

    pub async fn download_artifact(&self, task_id: &str, filename: &str) -> Result<Vec<u8>> {
        let key = format!("tasks/{}/{}", task_id, filename);

        debug!("Downloading artifact: bucket={}, key={}", self.bucket, key);

        let response = self.client
            .get_object()
            .bucket(&self.bucket)
            .key(&key)
            .send()
            .await?;

        let data = response.body.collect().await?;
        let bytes = data.into_bytes().to_vec();

        info!("Artifact downloaded successfully: {} bytes", bytes.len());

        Ok(bytes)
    }

    pub async fn list_artifacts(&self, task_id: &str) -> Result<Vec<String>> {
        let prefix = format!("tasks/{}/", task_id);

        debug!("Listing artifacts: bucket={}, prefix={}", self.bucket, prefix);

        let response = self.client
            .list_objects_v2()
            .bucket(&self.bucket)
            .prefix(&prefix)
            .send()
            .await?;

        let artifacts = response
            .contents()
            .iter()
            .filter_map(|obj| obj.key().map(|k| k.to_string()))
            .collect();

        Ok(artifacts)
    }

    pub async fn delete_task_artifacts(&self, task_id: &str) -> Result<()> {
        let artifacts = self.list_artifacts(task_id).await?;

        for key in artifacts {
            debug!("Deleting artifact: {}", key);
            self.client
                .delete_object()
                .bucket(&self.bucket)
                .key(&key)
                .send()
                .await?;
        }

        info!("Deleted all artifacts for task_id={}", task_id);

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    #[ignore] // Requires MinIO to be running
    async fn test_upload_download_artifact() {
        let storage = ArtifactStorage::new().await;
        let task_id = "test-task-001";
        let filename = "test.txt";
        let content = b"Hello, MAARS!".to_vec();

        // Upload
        let url = storage
            .upload_artifact(task_id, filename, content.clone())
            .await
            .unwrap();
        assert!(url.contains(filename));

        // Download
        let downloaded = storage.download_artifact(task_id, filename).await.unwrap();
        assert_eq!(downloaded, content);

        // Cleanup
        storage.delete_task_artifacts(task_id).await.unwrap();
    }
}

// Made with Bob
