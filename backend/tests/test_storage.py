import io

from PIL import Image

from extensions import db
from models import SiteProfile, SlideshowImage
from services.storage import StorageError, path_from_public_url, upload_image


class Response:
    def __init__(self, status_code=201):
        self.status_code = status_code


def png_file(size=(40, 30), color=(12, 90, 130, 255)):
    stream = io.BytesIO()
    Image.new("RGBA", size, color).save(stream, format="PNG")
    stream.seek(0)
    return stream


def test_upload_verifies_and_normalizes_image(app, monkeypatch):
    captured = {}

    def fake_post(url, headers, data, timeout):
        captured.update(url=url, headers=headers, data=data, timeout=timeout)
        return Response()

    monkeypatch.setattr("services.storage.requests.post", fake_post)
    with app.app_context():
        from werkzeug.datastructures import FileStorage

        stored = upload_image(FileStorage(stream=png_file(), filename="photo.png", content_type="image/png"), "profile")
        assert stored.path.startswith("profile/") and stored.path.endswith(".webp")
        assert stored.url.endswith(stored.path)
        assert captured["headers"]["apikey"] == "test-secret-key"
        assert "Authorization" not in captured["headers"]
        assert captured["headers"]["cache-control"] == "31536000"
        with Image.open(io.BytesIO(captured["data"])) as normalized:
            assert normalized.format == "WEBP"
            assert normalized.getexif() == {}


def test_upload_rejects_fake_image_and_unapproved_folder(app):
    from werkzeug.datastructures import FileStorage

    with app.app_context():
        fake = FileStorage(stream=io.BytesIO(b"not an image"), filename="fake.png", content_type="image/png")
        try:
            upload_image(fake, "profile")
            assert False, "Invalid image bytes should be rejected"
        except StorageError:
            pass
        try:
            upload_image(FileStorage(stream=png_file(), filename="photo.png", content_type="image/png"), "../private")
            assert False, "Unapproved folders should be rejected"
        except StorageError:
            pass


def test_public_url_path_is_accepted_only_for_managed_bucket(app):
    with app.app_context():
        managed = "https://test-project.supabase.co/storage/v1/object/public/site-media/slideshow/example.webp"
        assert path_from_public_url(managed) == "slideshow/example.webp"
        assert path_from_public_url("https://example.com/slideshow/example.webp") is None


def test_media_endpoint_returns_url_and_storage_path(authenticated, monkeypatch):
    monkeypatch.setattr("services.storage.requests.post", lambda *args, **kwargs: Response())
    response = authenticated.post(
        "/api/admin/media",
        data={"folder": "portfolio", "image": (png_file(), "project.png")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": "csrf-value"},
    )
    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["path"].startswith("portfolio/")
    assert payload["url"].endswith(payload["path"])


def test_profile_replacement_cleans_up_managed_image(app, authenticated, monkeypatch):
    cleaned = []
    with app.app_context():
        db.session.add(
            SiteProfile(
                profile_photo_url="https://test-project.supabase.co/storage/v1/object/public/site-media/profile/old.webp",
                profile_photo_path="profile/old.webp",
                phone="+233 50 916 3767",
                email="daniel.agblevor@outlook.com",
            )
        )
        db.session.commit()
    monkeypatch.setattr("api.admin.delete_image_safely", cleaned.append)
    response = authenticated.patch(
        "/api/admin/profile",
        json={"profile_photo_url": "https://images.example.test/new.webp"},
        headers={"X-CSRF-Token": "csrf-value"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["phone"] == "+233 50 916 3767"
    assert response.get_json()["data"]["email"] == "daniel.agblevor@outlook.com"
    assert cleaned == ["profile/old.webp"]


def test_slideshow_delete_cleans_up_managed_image(app, authenticated, monkeypatch):
    cleaned = []
    with app.app_context():
        image = SlideshowImage(
            image_url="https://test-project.supabase.co/storage/v1/object/public/site-media/slideshow/old.webp",
            storage_path="slideshow/old.webp",
            caption="A professional event",
            alt_text="Daniel speaking at a professional event",
        )
        db.session.add(image)
        db.session.commit()
        image_id = image.id
    monkeypatch.setattr("api.admin.delete_image_safely", cleaned.append)
    response = authenticated.delete(
        f"/api/admin/content/slideshow/{image_id}",
        headers={"X-CSRF-Token": "csrf-value"},
    )
    assert response.status_code == 200
    assert cleaned == ["slideshow/old.webp"]
