import unittest
from io import BytesIO

from PIL import Image

from app.avatar_images import MAX_AVATAR_BYTES, normalize_avatar


def make_image(image_format: str, size: tuple[int, int] = (900, 600)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (22, 128, 120)).save(buffer, format=image_format)
    return buffer.getvalue()


class AvatarImageTests(unittest.TestCase):
    def test_valid_png_is_resized_and_reencoded_as_webp(self):
        output = normalize_avatar(make_image("PNG"))
        with Image.open(BytesIO(output)) as avatar:
            self.assertEqual(avatar.format, "WEBP")
            self.assertLessEqual(max(avatar.size), 512)

    def test_valid_jpeg_is_accepted(self):
        output = normalize_avatar(make_image("JPEG", (300, 300)))
        with Image.open(BytesIO(output)) as avatar:
            self.assertEqual(avatar.format, "WEBP")

    def test_unsupported_format_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "JPG, PNG o WebP"):
            normalize_avatar(make_image("GIF"))

    def test_non_image_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_avatar(b"esto no es una imagen")

    def test_oversized_upload_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "2 MB"):
            normalize_avatar(b"x" * (MAX_AVATAR_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
