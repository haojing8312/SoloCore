from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator

class VerticalAlignmentType(str, Enum):
    BOTTOM = "bottom"
    CENTER = "center"
    TOP = "top"

class TextOverflowStrategy(str, Enum):
    EXCEED_MAX_NUMBER_OF_LINES = "exceed_lines"
    EXCEED_MAX_WIDTH_RATIO_IN_LAST_LINE = "exceed_width"

class VerticalAlignment(BaseModel):
    """Represents a vertical alignment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    align: VerticalAlignmentType = VerticalAlignmentType.BOTTOM
    offset: float = 0.0  # from -1.0 to 1.0

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: float) -> float:
        if not -1.0 <= v <= 1.0:
            raise ValueError("offset must be between -1.0 and 1.0")
        return v

class SubtitleLayoutOptions(BaseModel):
    """Options for configuring the subtitle layout."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    x_words_space: int = 0  # you can use padding via css instead of this parameter
    y_words_space: int = 0
    max_width_ratio: float = 0.8
    max_number_of_lines: int = 2
    min_number_of_lines: int = 1
    on_text_overflow_strategy: TextOverflowStrategy = TextOverflowStrategy.EXCEED_MAX_NUMBER_OF_LINES
    vertical_align: VerticalAlignment = Field(default_factory=VerticalAlignment)

    @field_validator("max_width_ratio")
    @classmethod
    def validate_ratio(cls, v: float) -> float:
        if not 0.0 < v <= 1.0:
            raise ValueError("max_width_ratio must be between 0.0 and 1.0 (exclusive-inclusive)")
        return v

    @field_validator("max_number_of_lines", "min_number_of_lines")
    @classmethod
    def validate_positive_int(cls, v: int, info) -> int:
        if v <= 0:
            raise ValueError(f"{info.field_name} must be a positive integer")
        return v

    @field_validator("max_number_of_lines")
    @classmethod
    def validate_line_consistency(cls, v: int, info) -> int:
        min_lines = info.data.get("min_number_of_lines")
        if min_lines and v < min_lines:
            raise ValueError("max_number_of_lines cannot be less than min_number_of_lines")
        return v
