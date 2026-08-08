from jarvis.core.engine import JarvisEngine
from jarvis.ui.tui.screens.modals.model_modal import ModelModal


def test_model_modal_safe_config_access():
    engine = JarvisEngine()
    engine.config = None  # engine.config is None prior to initialization

    modal = ModelModal(engine=engine)
    assert modal._get_active_provider() == "groq"
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
    assert dismissed_result["provider"] == "groq"


def test_model_modal_only_provider_filter():
    engine = JarvisEngine()
    modal = ModelModal(engine=engine, only_provider="opencode")
    data = modal._build_models_data()
    assert isinstance(data, list)
    for item in data:
        assert item["provider"] == "opencode"
    assert modal.dialog._title_text.startswith("Select OpenCode")


def test_model_modal_ctrl_a_action_open_connect():
    engine = JarvisEngine()
    modal = ModelModal(engine=engine)

    dismissed = False

    def mock_dismiss(result=None):
        nonlocal dismissed
        dismissed = True

    modal.dismiss = mock_dismiss

    called_target = False

    class DummyMainScreen:
        def action_open_connect(self):
            nonlocal called_target
            called_target = True

    dummy_main = DummyMainScreen()

    class DummyApp:
        screen_stack = [dummy_main, modal]

        def set_timer(self, delay, callback):
            callback()

    modal._app = DummyApp()  # type: ignore[attr-defined]

    modal.action_open_connect()
    assert dismissed is True
    assert called_target is True


