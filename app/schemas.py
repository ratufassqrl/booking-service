from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    capacity: int = Field(ge=1, le=20)


class RoomOut(RoomIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BookingIn(BaseModel):
    room_id: int
    guest_name: str = Field(min_length=1, max_length=100)
    check_in: date
    check_out: date

    @model_validator(mode="after")
    def check_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out должен быть позже check_in")
        return self


class BookingOut(BookingIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
