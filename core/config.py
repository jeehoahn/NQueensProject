from dataclasses import dataclass


@dataclass
class AppConfig:
    board_size: int = 8

    def __post_init__(self):
        if self.board_size < 1:
            raise ValueError("Board size must be at least 1.")
