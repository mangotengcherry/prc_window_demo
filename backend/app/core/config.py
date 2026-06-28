from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "EDS BIN Process Window Workbench API"
    random_seed: int = 42
    lot_count: int = 220
    min_wafers: int = 10
    max_wafers: int = 22
    bin_count: int = 600


settings = Settings()
