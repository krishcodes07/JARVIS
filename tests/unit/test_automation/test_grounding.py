"""
Unit tests for UIAGrounder and VisualGrounder.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from jarvis.automation.grounding.uia import UIAGrounder
from jarvis.automation.grounding.vision import VisualGrounder
from jarvis.automation.schemas import UIElementInfo


def test_uia_grounder_format_elements() -> None:
    grounder = UIAGrounder()
    elements = [
        UIElementInfo(
            id=1,
            name="File",
            control_type="MenuItem",
            automation_id="Item 1",
            bounding_box=(0, 0, 50, 20),
            center_point=(25, 10),
        ),
        UIElementInfo(
            id=2,
            name="Text Editor",
            control_type="Edit",
            automation_id="15",
            bounding_box=(0, 20, 800, 600),
            center_point=(400, 320),
        ),
    ]
    formatted = grounder.format_elements_for_prompt(elements)
    assert "| 1 | MenuItem | File | (25, 10) | Item 1 |" in formatted
    assert "| 2 | Edit | Text Editor | (400, 320) | 15 |" in formatted


def test_visual_grounder_som_annotation() -> None:
    grounder = VisualGrounder()

    # Create dummy screenshot
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dummy_screen = tmp_path / "test_screen.png"
        img = Image.new("RGB", (400, 300), color=(50, 50, 50))
        img.save(dummy_screen)

        elements = [
            UIElementInfo(
                id=1,
                name="OK Button",
                control_type="Button",
                bounding_box=(50, 50, 80, 30),
                center_point=(90, 65),
            ),
        ]

        som_path = grounder.annotate_set_of_marks(dummy_screen, elements)
        assert som_path.exists()
        with Image.open(som_path) as annotated_img:
            assert annotated_img.size == (400, 300)


def test_visual_grounder_delta_computation() -> None:
    grounder = VisualGrounder()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        img1_path = tmp_path / "img1.png"
        img2_path = tmp_path / "img2.png"

        img1 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        img1.save(img1_path)

        # Identical image -> 0 delta
        delta_same = grounder.compute_visual_delta(img1_path, img1_path)
        assert delta_same == 0.0

        # Inverted image -> high delta
        img2 = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img2.save(img2_path)
        delta_diff = grounder.compute_visual_delta(img1_path, img2_path)
        assert delta_diff > 0.9
