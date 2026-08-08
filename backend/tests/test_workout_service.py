from app.services.workout_service import infer_activity_type


class StubActivityClassifier:
    def classify(self, context):
        assert context["filename"] == "morning-bike.gpx"
        return "cycling"


def test_activity_inference_from_filename():
    class GPX:
        name = None
        description = None
        creator = None
        tracks = []

    assert infer_activity_type(GPX(), "morning-bike.gpx", StubActivityClassifier()) == "cycling"


def test_activity_inference_falls_back_to_unknown():
    class FailingClassifier:
        def classify(self, context):
            raise RuntimeError("classifier unavailable")

    class GPX:
        name = None
        description = None
        creator = None
        tracks = []

    assert infer_activity_type(GPX(), "session.gpx", FailingClassifier()) == "unknown"


def test_infer_activity_type_handles_missing_type_attribute():
    class GPX:
        name = None
        description = None
        creator = None
        tracks = []

    assert infer_activity_type(GPX(), "session.gpx", StubActivityClassifier()) == "cycling"
