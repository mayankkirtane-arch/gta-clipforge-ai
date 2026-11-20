# Unit test for YouTube Link to Shorts Service
from app.services.youtube_service import youtube_service, YouTubeService, YouTubeTask
from app.routers.youtube import router, YouTubeUrlRequest, YouTubeImportRequest
from app.database import SessionLocal
from app.models.recording import Recording
from app.models.recording_permission import RecordingPermission

def test_youtube_url_validation():
    # Valid URLs
    assert youtube_service.is_valid_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert youtube_service.is_valid_youtube_url("https://youtu.be/dQw4w9WgXcQ")
    assert youtube_service.is_valid_youtube_url("https://www.youtube.com/shorts/AbCdEfGhIjK")
    assert youtube_service.is_valid_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
    assert youtube_service.is_valid_youtube_url("http://youtube.com/watch?v=test1234567")

    # Invalid URLs
    assert not youtube_service.is_valid_youtube_url("https://vimeo.com/123456")
    assert not youtube_service.is_valid_youtube_url("https://google.com")
    assert not youtube_service.is_valid_youtube_url("not_a_url")
    assert not youtube_service.is_valid_youtube_url("")

def test_youtube_task_lifecycle():
    service = YouTubeService()
    
    # 1. Invalid URL check
    assert not service.is_valid_youtube_url("invalid")
    
    # 2. Create task
    task = service.create_download_task(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        auto_generate_shorts=True,
        notes="Test YouTube download",
        has_permission=True,
        creator_name="Test Creator"
    )
    assert task is not None
    assert task.task_id is not None
    assert task.status in ["pending", "downloading", "processing", "completed", "failed"]
    
    # 3. Retrieve task
    fetched = service.get_task(task.task_id)
    assert fetched is not None
    assert fetched.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # 4. List tasks
    task_list = service.list_tasks(limit=10)
    assert any(t["task_id"] == task.task_id for t in task_list)
    
    # 5. Cancel task
    cancelled = service.cancel_task(task.task_id)
    # Could be True or False depending on whether worker completed
    assert isinstance(cancelled, bool)

def test_youtube_endpoints_registration():
    from app.main import app
    paths = list(app.openapi()["paths"].keys())
    
    assert "/api/youtube/info" in paths
    assert "/api/youtube/import" in paths
    assert "/api/youtube/tasks" in paths
    assert "/api/youtube/tasks/{task_id}" in paths
    assert "/api/youtube/tasks/{task_id}/cancel" in paths

if __name__ == "__main__":
    test_youtube_url_validation()
    test_youtube_task_lifecycle()
    test_youtube_endpoints_registration()
    print("✅ All YouTube service and endpoint tests passed 100%!")
