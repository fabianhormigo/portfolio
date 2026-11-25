"""Cliente MCP de demostración: arranca server.py por stdio, descubre sus herramientas y las llama.

Hace de «agente» con un guion fijo (sin LLM ni claves). Conectado a Claude u otro cliente MCP,
es el modelo quien elige las herramientas; el protocolo es el mismo.
"""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

AQUI = Path(__file__).resolve().parent

PASOS = [
    ("Indexar la documentación", "biblioteca_indexar", {}),
    ("¿Cada cuánto se calibra el sensor?", "biblioteca_consultar",
     {"pregunta": "cada cuánto se calibra el sensor", "max_pasajes": 1}),
    ("Incertidumbre de un área a·b (GUM y Monte Carlo)", "incertidumbre_propagar",
     {"modelo": "a*b", "entradas": {"a": {"valor": 3.75, "u": 0.01}, "b": {"valor": 2.65, "u": 0.01}}}),
]


async def main() -> None:
    srv = StdioServerParameters(command=sys.executable, args=[str(AQUI / "server.py")], cwd=str(AQUI))
    async with stdio_client(srv) as (leer, escribir), ClientSession(leer, escribir) as s:
        await s.initialize()
        herramientas = (await s.list_tools()).tools
        print(f"Herramientas descubiertas ({len(herramientas)}):", ", ".join(t.name for t in herramientas))
        for titulo, nombre, args in PASOS:
            r = await s.call_tool(nombre, args)
            if r.isError:
                raise RuntimeError(f"{nombre}: {r.content[0].text}")
            print(f"\n>>> {titulo}\n[{nombre}]\n{r.content[0].text[:900]}")


if __name__ == "__main__":
    asyncio.run(main())
