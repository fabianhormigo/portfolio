"""Mini-CRM con ETL fiable: claves normalizadas, deduplicación, webhooks idempotentes y reintentos con backoff.

Garantías: un mismo evento (event_id) nunca se aplica dos veces; si el procesamiento falla a mitad,
la transacción se revierte y el evento puede reintentarse; los errores transitorios se reintentan con
backoff exponencial y los demás se propagan sin ocultarse. SQLite + stdlib; datos de ejemplo ficticios.
"""
from __future__ import annotations

import re
import sqlite3
import time
import unicodedata

ESTADOS = {"nuevo", "contactado", "ganado", "perdido"}


def _sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalizar_nombre(n: str) -> str:
    return re.sub(r"\s+", " ", _sin_acentos(n).lower()).strip()


def normalizar_email(e: str) -> str:
    return e.strip().lower()


def normalizar_telefono(t: str) -> str:
    return re.sub(r"\D", "", t)[-9:]


def con_reintentos(fn, intentos: int = 4, base: float = 0.5, factor: float = 2.0,
                   transitorios=(ConnectionError, TimeoutError), sleep=time.sleep):
    """Reintenta solo errores transitorios; espera base·factor^i. El último fallo se propaga."""
    for i in range(intentos):
        try:
            return fn()
        except transitorios:
            if i == intentos - 1:
                raise
            sleep(base * factor ** i)


class Crm:
    def __init__(self, ruta: str = ":memory:"):
        self.db = sqlite3.connect(ruta)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS clientes(
                id INTEGER PRIMARY KEY, nombre TEXT, email TEXT, telefono TEXT, estado TEXT);
            CREATE TABLE IF NOT EXISTS eventos(id TEXT PRIMARY KEY);
        """)

    def procesar_evento(self, event_id: str, payload: dict) -> str:
        """Devuelve 'aplicado' o 'duplicado'. Atómico: evento y cambio se confirman juntos."""
        with self.db:
            try:
                self.db.execute("INSERT INTO eventos VALUES (?)", (event_id,))
            except sqlite3.IntegrityError:
                return "duplicado"
            estado = payload.get("estado", "nuevo")
            if estado not in ESTADOS:
                raise ValueError(f"estado no válido: {estado!r}")
            nombre = normalizar_nombre(payload.get("nombre", ""))
            email = normalizar_email(payload.get("email", ""))
            tel = normalizar_telefono(payload.get("telefono", ""))
            fila = self.db.execute(
                "SELECT id FROM clientes WHERE (email != '' AND email = ?) OR (telefono != '' AND telefono = ?)",
                (email, tel)).fetchone()
            if fila:
                self.db.execute(
                    "UPDATE clientes SET nombre = COALESCE(NULLIF(?, ''), nombre), "
                    "email = COALESCE(NULLIF(?, ''), email), telefono = COALESCE(NULLIF(?, ''), telefono), "
                    "estado = ? WHERE id = ?", (nombre, email, tel, estado, fila[0]))
            else:
                self.db.execute("INSERT INTO clientes(nombre, email, telefono, estado) VALUES (?,?,?,?)",
                                (nombre, email, tel, estado))
            return "aplicado"

    def clientes(self) -> list[tuple]:
        return self.db.execute("SELECT nombre, email, telefono, estado FROM clientes ORDER BY id").fetchall()
