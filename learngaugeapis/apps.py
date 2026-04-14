from django.apps import AppConfig


class LearngaugeapisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'learngaugeapis'

    def ready(self):
        from decouple import config

        model_path = config("ML_MODEL_PATH", default=None)
        data_dir = config("ML_DATA_DIR", default=None)

        if model_path and data_dir:
            from learngaugeapis.ml_pipeline import initialize_pipelines
            initialize_pipelines(model_path, data_dir)
