from jarvis.core.engine import JarvisEngine
from jarvis.ui.tui.screens.modals.model_modal import ModelModal


def test_model_modal_safe_config_access():
    engine = JarvisEngine()
    engine.config = None  # engine.config is None prior to initialization

    modal = ModelModal(engine=engine)
    assert modal._get_active_provider() == "openrouter"
    assert modal._get_active_model() == ""

    data = modal._build_models_data()
    assert isinstance(data, list)

    class DummyOption:
        id = "custom-model-id"

    class DummyEvent:
        option_id = "custom-model-id"
        option = DummyOption()

    event = DummyEvent()
    dismissed_result = None

    def mock_dismiss(result):
        nonlocal dismissed_result
        dismissed_result = result

    modal.dismiss = mock_dismiss  # type: ignore[assignment]
    modal.on_option_list_option_selected(event)  # type: ignore[arg-type]

    assert dismissed_result is not None
    assert dismissed_result["id"] == "custom-model-id"
    assert dismissed_result["provider"] == "openrouter"
