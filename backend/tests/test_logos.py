from io import BytesIO

import pytest
from PIL import Image

from app.logos import normalize_logo


def test_normalizes_and_strips_metadata():
    source = BytesIO()
    Image.new("RGB", (700, 350), "red").save(source, format="JPEG", comment=b"private metadata")
    with Image.open(BytesIO(normalize_logo(source.getvalue()))) as result:
        assert result.size == (256, 128)
        assert result.format == "PNG"
        assert not result.info


@pytest.mark.parametrize(
    "data",
    [b"<svg></svg>", b"not an image", b"", b"x" * (2 * 1024 * 1024 + 1)],
    ids=["svg", "invalid", "empty", "oversized"],
)
def test_rejects_invalid_files(data):
    with pytest.raises(ValueError):
        normalize_logo(data)


def test_rejects_excessive_dimensions():
    source = BytesIO()
    Image.new("RGB", (4097, 1)).save(source, format="PNG")
    with pytest.raises(ValueError):
        normalize_logo(source.getvalue())
