from chat import _partir_respuesta, validar_accion


def test_separa_prosa_y_accion_con_fence():
    t, a = _partir_respuesta('Aquí va.\n```json\n{"accion":{"tipo":"chart","chart":"bar"}}\n```')
    assert t == "Aquí va." and a == {"tipo": "chart", "chart": "bar"}


def test_accion_sin_fence_y_sin_envoltorio():
    t, a = _partir_respuesta('Filtro aplicado {"tipo":"filter","anio_min":2020}')
    assert t == "Filtro aplicado" and a["anio_min"] == 2020


def test_texto_sin_accion():
    assert _partir_respuesta("Solo texto {no es json}") == ("Solo texto {no es json}", None)


def test_corrige_tildes_en_el_sector():
    a = validar_accion({"tipo": "filter", "sectores": ["Construcción/Obra civil"]}, ["Construccion/Obra civil"])
    assert a["sectores"] == ["Construccion/Obra civil"]


def test_sector_inexistente_anula_la_accion():
    assert validar_accion({"tipo": "filter", "sectores": ["Aeroespacial"]}, ["Energia"]) is None
