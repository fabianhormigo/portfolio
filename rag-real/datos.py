"""Corpus y preguntas de evaluación. TODO ES FICTICIO: ninguna norma real."""

# (sección, texto en versión 2022, texto en versión 2025)
_SENSOR = [
    ("3.1", "El sensor de inclinación se calibrará cada 12 meses en laboratorio.",
            "El sensor de inclinación se calibrará cada 9 meses en laboratorio."),
    ("3.2", "Tras un golpe o caída el equipo se verificará antes de volver a usarse.",
            "Tras un golpe o caída el equipo se recalibrará antes de volver a usarse."),
    ("4.1", "En cada profundidad se tomarán dos lecturas en posiciones opuestas.",
            "En cada profundidad se tomarán cuatro lecturas en posiciones opuestas dos a dos."),
    ("4.2", "El paso de medida a lo largo del tubo será de 0,5 metros.",
            "El paso de medida a lo largo del tubo será de 0,5 metros."),
    ("4.3", "La sonda reposará 5 minutos en el fondo para estabilizar la temperatura.",
            "La sonda reposará 10 minutos en el fondo para estabilizar la temperatura."),
    ("5.1", "La tolerancia entre lecturas redundantes será de 30 unidades.",
            "La tolerancia entre lecturas redundantes será de 20 unidades."),
    ("5.2", "Si se supera la tolerancia se repetirá la lectura una vez.",
            "Si se supera la tolerancia se repetirá la lectura dos veces y se anotará la incidencia."),
    ("6.1", "El informe indicará el desplazamiento acumulado desde el fondo del tubo.",
            "El informe indicará el desplazamiento acumulado y el incremental por tramo."),
    ("6.2", "La incertidumbre expandida se expresará con factor de cobertura 2.",
            "La incertidumbre expandida se expresará con factor de cobertura 2 y su distribución."),
    ("7.1", "El equipo se almacenará entre 5 y 35 grados centígrados.",
            "El equipo se almacenará entre 0 y 40 grados centígrados."),
    ("7.2", "Las baterías no se guardarán completamente cargadas más de un mes.",
            "Las baterías no se guardarán completamente cargadas más de dos semanas."),
    ("8.1", "Los ficheros brutos se conservarán durante 5 años.",
            "Los ficheros brutos se conservarán durante 10 años."),
]

_HORMIGON = [
    ("2.1", "El recubrimiento mínimo de las armaduras será de 40 mm en ambiente expuesto.",
            "El recubrimiento mínimo de las armaduras será de 45 mm en ambiente expuesto."),
    ("2.2", "La resistencia característica del hormigón no será inferior a 25 MPa.",
            "La resistencia característica del hormigón no será inferior a 30 MPa."),
    ("2.3", "La relación agua cemento máxima será de 0,55.",
            "La relación agua cemento máxima será de 0,50."),
    ("3.1", "El curado se mantendrá al menos 5 días.",
            "El curado se mantendrá al menos 7 días."),
    ("3.2", "Se tomarán 3 probetas por cada lote de hormigonado.",
            "Se tomarán 5 probetas por cada lote de hormigonado."),
    ("3.3", "No se hormigonará con temperatura ambiente inferior a 5 grados.",
            "No se hormigonará con temperatura ambiente inferior a 5 grados."),
]

CORPUS = [
    {"id": f"{pref}-{ver}-{sec}", "norma": norma, "version": ver, "fecha": f"{ver}-01-01", "seccion": sec, "texto": t[i]}
    for norma, pref, tabla in (("NT-SENSOR", "S", _SENSOR), ("NT-HORMIGON", "H", _HORMIGON))
    for sec, *t in tabla
    for i, ver in enumerate(("2022", "2025"))
]

# (pregunta redactada con otras palabras, norma, versión, id correcto, texto que debe aparecer en la respuesta)
_P = [
    ("¿Cada cuánto hay que mandar el inclinómetro a calibrar?", "NT-SENSOR", "2022", "S-2022-3.1", "12"),
    ("¿Con qué periodicidad se calibra la sonda?", "NT-SENSOR", "2025", "S-2025-3.1", "9"),
    ("Se me ha caído el equipo, ¿qué tengo que hacer?", "NT-SENSOR", "2025", "S-2025-3.2", "recalibr"),
    ("¿Cuántas medidas se hacen en cada cota?", "NT-SENSOR", "2022", "S-2022-4.1", "dos"),
    ("¿Cuántas medidas se hacen en cada cota?", "NT-SENSOR", "2025", "S-2025-4.1", "cuatro"),
    ("¿Cada cuántos metros se lee dentro de la tubería?", "NT-SENSOR", "2025", "S-2025-4.2", "0,5"),
    ("¿Cuánto tiempo espero abajo para que se iguale la temperatura?", "NT-SENSOR", "2022", "S-2022-4.3", "5"),
    ("¿Cuánto tiempo espero abajo para que se iguale la temperatura?", "NT-SENSOR", "2025", "S-2025-4.3", "10"),
    ("¿Qué diferencia máxima se admite entre lecturas repetidas?", "NT-SENSOR", "2025", "S-2025-5.1", "20"),
    ("¿Qué hago si dos lecturas difieren más de lo permitido?", "NT-SENSOR", "2022", "S-2022-5.2", "repet"),
    ("¿Qué desplazamientos tiene que recoger el documento final?", "NT-SENSOR", "2025", "S-2025-6.1", "incremental"),
    ("¿A qué temperatura puedo guardar el aparato?", "NT-SENSOR", "2025", "S-2025-7.1", "40"),
    ("¿Cuánto tiempo pueden estar las pilas llenas sin usarse?", "NT-SENSOR", "2022", "S-2022-7.2", "mes"),
    ("¿Durante cuántos años guardo los datos originales?", "NT-SENSOR", "2025", "S-2025-8.1", "10"),
    ("¿Cuánto hormigón debe tapar como mínimo el acero?", "NT-HORMIGON", "2022", "H-2022-2.1", "40"),
    ("¿Cuánto hormigón debe tapar como mínimo el acero?", "NT-HORMIGON", "2025", "H-2025-2.1", "45"),
    ("¿Qué resistencia mínima se exige?", "NT-HORMIGON", "2025", "H-2025-2.2", "30"),
    ("¿Cuál es el tope de agua respecto a cemento?", "NT-HORMIGON", "2022", "H-2022-2.3", "0,55"),
    ("¿Cuántos días hay que curar la pieza?", "NT-HORMIGON", "2025", "H-2025-3.1", "7"),
    ("¿Cuántas muestras se sacan por lote?", "NT-HORMIGON", "2022", "H-2022-3.2", "3"),
    ("¿Con cuánto frío está prohibido hormigonar?", "NT-HORMIGON", "2025", "H-2025-3.3", "5"),
]

# preguntas sin respuesta en el corpus: lo correcto es negarse
_SIN = [
    ("¿Cuánto cuesta calibrar el sensor?", "NT-SENSOR", "2025"),
    ("¿Qué marca de inclinómetro es obligatoria?", "NT-SENSOR", "2022"),
    ("¿Qué titulación debe tener el operador?", "NT-SENSOR", "2025"),
    ("¿Cuál es la cuantía mínima de acero en vigas?", "NT-HORMIGON", "2025"),
    ("¿Qué tipo de árido está prohibido?", "NT-HORMIGON", "2022"),
    ("¿A los cuántos días se puede desencofrar?", "NT-HORMIGON", "2025"),
]

# preguntas RESERVADAS: no se miraron para corregir el prompt
_R = [
    ("¿Qué pasa si las medidas redundantes no entran en el margen?", "NT-SENSOR", "2025", "S-2025-5.2", "dos"),
    ("¿Con qué factor k se da la incertidumbre?", "NT-SENSOR", "2022", "S-2022-6.2", "2"),
    ("¿Cuántos años se archivan los ficheros brutos?", "NT-SENSOR", "2022", "S-2022-8.1", "5"),
    ("¿Qué margen entre lecturas se acepta?", "NT-SENSOR", "2022", "S-2022-5.1", "30"),
    ("¿Cuál es el máximo de temperatura para el almacenaje?", "NT-SENSOR", "2022", "S-2022-7.1", "35"),
    ("¿Qué se hace si el aparato recibe un golpe?", "NT-SENSOR", "2022", "S-2022-3.2", "verific"),
    ("¿Cada qué distancia se toman puntos en el tubo?", "NT-SENSOR", "2022", "S-2022-4.2", "0,5"),
    ("¿Qué MPa se piden como mínimo al hormigón?", "NT-HORMIGON", "2022", "H-2022-2.2", "25"),
    ("¿Qué duración mínima tiene el curado?", "NT-HORMIGON", "2022", "H-2022-3.1", "5"),
    ("¿Cuántas probetas corresponden a cada lote?", "NT-HORMIGON", "2025", "H-2025-3.2", "5"),
]
_RSIN = [("¿Quién firma el informe?", "NT-SENSOR", "2025"), ("¿Qué tipo de cemento es obligatorio?", "NT-HORMIGON", "2025"),
         ("¿Cuántos años de garantía tiene el sensor?", "NT-SENSOR", "2022")]
RESERVADAS = ([{"pregunta": q, "norma": n, "version": v, "gold": g, "esperado": e} for q, n, v, g, e in _R] +
              [{"pregunta": q, "norma": n, "version": v, "gold": None, "esperado": None} for q, n, v in _RSIN])

PREGUNTAS = ([{"pregunta": q, "norma": n, "version": v, "gold": g, "esperado": e} for q, n, v, g, e in _P] +
             [{"pregunta": q, "norma": n, "version": v, "gold": None, "esperado": None} for q, n, v in _SIN])
