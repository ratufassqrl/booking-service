"""REST-сервис бронирования номеров.

Наблюдаемость:
- трассировки, метрики HTTP и SQL-запросов, логи собирает OpenTelemetry
  автоматически (запуск через `opentelemetry-instrument`, см. Dockerfile);
- свои бизнес-метрики ниже: bookings_created, booking_conflicts, booking_errors.
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from opentelemetry import metrics
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base, engine, get_session
from app.models import Booking, Room
from app.schemas import BookingIn, BookingOut, RoomIn, RoomOut

APP_VERSION = os.getenv("APP_VERSION", "dev")

# --- Логи -------------------------------------------------------------------
# Пишем в stdout (видно в `docker compose logs`) и пробрасываем в корневой
# логгер, откуда OpenTelemetry отправляет записи в Loki.
log = logging.getLogger("booking")
log.setLevel(logging.INFO)
if not log.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    log.addHandler(handler)

# --- Метрики ----------------------------------------------------------------
# Без opentelemetry-instrument (например, в тестах) это «пустые» счётчики.
meter = metrics.get_meter("booking-service")
bookings_created = meter.create_counter("bookings_created", description="Созданные брони")
booking_conflicts = meter.create_counter("booking_conflicts", description="Отказы из-за пересечения дат")
booking_errors = meter.create_counter("booking_errors", description="Ответы сервиса с кодом 5xx")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    log.info("service started, version=%s", APP_VERSION)
    yield


SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI(title="Booking service", version=APP_VERSION, lifespan=lifespan)


@app.middleware("http")
async def count_errors(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        response = JSONResponse({"detail": "internal error"}, status_code=500)
    if response.status_code >= 500:
        booking_errors.add(1, {"path": request.url.path})
    log.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response


# --- Служебные эндпоинты ----------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    """Какая версия артефакта сейчас развернута."""
    return {"version": APP_VERSION}


@app.get("/debug/error")
def debug_error():
    """Специально падает с 500 — для проверки алерта."""
    raise RuntimeError("тестовая ошибка для проверки наблюдаемости")


# --- Номера -----------------------------------------------------------------
@app.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(data: RoomIn, session: SessionDep):
    room = Room(**data.model_dump())
    session.add(room)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "номер с таким названием уже есть") from None
    log.info("room created id=%s name=%s", room.id, room.name)
    return room


@app.get("/rooms", response_model=list[RoomOut])
def list_rooms(session: SessionDep):
    return session.scalars(select(Room).order_by(Room.id)).all()


# --- Брони ------------------------------------------------------------------
@app.post("/bookings", response_model=BookingOut, status_code=201)
def create_booking(data: BookingIn, session: SessionDep):
    if session.get(Room, data.room_id) is None:
        raise HTTPException(404, "номер не найден")

    overlap = session.scalars(
        select(Booking).where(
            Booking.room_id == data.room_id,
            Booking.check_in < data.check_out,
            Booking.check_out > data.check_in,
        )
    ).first()
    if overlap:
        booking_conflicts.add(1)
        log.warning("booking conflict room=%s with booking=%s", data.room_id, overlap.id)
        raise HTTPException(409, f"номер уже занят (бронь {overlap.id})")

    booking = Booking(**data.model_dump())
    session.add(booking)
    session.commit()
    bookings_created.add(1, {"room_id": str(booking.room_id)})
    log.info("booking created id=%s room=%s", booking.id, booking.room_id)
    return booking


@app.get("/bookings", response_model=list[BookingOut])
def list_bookings(session: SessionDep, room_id: int | None = None):
    query = select(Booking).order_by(Booking.check_in)
    if room_id is not None:
        query = query.where(Booking.room_id == room_id)
    return session.scalars(query).all()


@app.get("/bookings/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, session: SessionDep):
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(404, "бронь не найдена")
    return booking


@app.delete("/bookings/{booking_id}", status_code=204)
def cancel_booking(booking_id: int, session: SessionDep):
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(404, "бронь не найдена")
    session.delete(booking)
    session.commit()
    log.info("booking cancelled id=%s", booking_id)
