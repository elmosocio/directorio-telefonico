"""
Casos de prueba para el Directorio Telefónico.

Ejecutar con:
    python -m unittest test_directorio_telefonico.py -v
o bien:
    pytest test_directorio_telefonico.py -v
"""

import csv
import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from directorio_telefonico import Contacto, Directorio, ValidationError


# ---------------------------------------------------------------------------
class TestValidacionNombre(unittest.TestCase):
    def test_nombre_valido_no_lanza(self):
        self.assertTrue(Contacto.validar_nombre("Juan Pérez"))

    def test_nombre_muy_corto(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_nombre("Al X")  # < 5 caracteres tras strip

    def test_nombre_una_sola_palabra(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_nombre("Juanjose")

    def test_nombre_con_numeros(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_nombre("Juan Perez3")

    def test_nombre_con_acentos_es_valido(self):
        self.assertTrue(Contacto.validar_nombre("José Ñúñez"))

    def test_nombre_no_string(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_nombre(12345)  # type: ignore[arg-type]


class TestValidacionTelefono(unittest.TestCase):
    def test_telefono_valido(self):
        self.assertTrue(Contacto.validar_telefono("5512345678"))

    def test_telefono_corto(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_telefono("12345")

    def test_telefono_largo(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_telefono("551234567890")

    def test_telefono_no_numerico(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_telefono("55-1234-56")


class TestValidacionCorreo(unittest.TestCase):
    def test_correo_valido(self):
        self.assertTrue(Contacto.validar_correo("juan@empresa.com"))

    def test_correo_sin_arroba(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_correo("juan.empresa.com")

    def test_correo_sin_dominio(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_correo("juan@")

    def test_correo_sin_extension(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_correo("juan@empresa")


class TestValidacionFecha(unittest.TestCase):
    def test_fecha_valida(self):
        self.assertTrue(Contacto.validar_fecha_nacimiento("1990-05-15"))

    def test_fecha_formato_incorrecto(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_fecha_nacimiento("15-05-1990")

    def test_fecha_dia_invalido_para_el_mes(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_fecha_nacimiento("2023-02-30")  # febrero no tiene día 30

    def test_fecha_anterior_al_minimo(self):
        with self.assertRaises(ValidationError):
            Contacto.validar_fecha_nacimiento("1900-01-01")

    def test_fecha_futura(self):
        manana = (date.today() + timedelta(days=1)).isoformat()
        with self.assertRaises(ValidationError):
            Contacto.validar_fecha_nacimiento(manana)

    def test_fecha_limite_minima_es_valida(self):
        self.assertTrue(Contacto.validar_fecha_nacimiento("1925-01-01"))


# ---------------------------------------------------------------------------
class TestContacto(unittest.TestCase):
    def _crear_contacto(self, **overrides):
        datos = dict(
            id=1,
            nombre="Juan Pérez",
            telefono="5512345678",
            fecha_nacimiento="1990-05-15",
            correo="juan@empresa.com",
            area="Ventas",
            areas_validas={"Ventas"},
        )
        datos.update(overrides)
        return Contacto(**datos)

    def test_str_formato_esperado(self):
        c = self._crear_contacto()
        self.assertEqual(str(c), "ID: 1 | Juan Pérez | ☎ 5512345678 | Ventas")

    def test_to_dict(self):
        c = self._crear_contacto()
        self.assertEqual(
            c.to_dict(),
            {
                "id": 1,
                "nombre": "Juan Pérez",
                "telefono": "5512345678",
                "fecha_nacimiento": "1990-05-15",
                "correo": "juan@empresa.com",
                "area": "Ventas",
            },
        )

    def test_from_dict_reconstruye_contacto_equivalente(self):
        original = self._crear_contacto()
        clon = Contacto.from_dict(original.to_dict(), areas_validas={"Ventas"})
        self.assertEqual(original, clon)
        self.assertEqual(str(original), str(clon))

    def test_id_no_positivo_lanza_error(self):
        with self.assertRaises(ValidationError):
            self._crear_contacto(id=0)

    def test_area_fuera_de_catalogo_lanza_error(self):
        with self.assertRaises(ValidationError):
            self._crear_contacto(area="Marketing", areas_validas={"Ventas"})

    def test_igualdad_por_id(self):
        c1 = self._crear_contacto(id=7)
        c2 = self._crear_contacto(id=7, telefono="5500000000")
        self.assertEqual(c1, c2)


# ---------------------------------------------------------------------------
class TestDirectorio(unittest.TestCase):
    def setUp(self):
        fd, self.ruta_temporal = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.ruta_temporal)  # que Directorio parta de "no existe"
        self.directorio = Directorio(ruta_datos=self.ruta_temporal, formato="json")

    def tearDown(self):
        if os.path.exists(self.ruta_temporal):
            os.remove(self.ruta_temporal)

    def _agregar_contacto_valido(self, **overrides):
        datos = dict(
            nombre="Ana García",
            telefono="5511111111",
            fecha_nacimiento="1995-03-20",
            correo="ana@empresa.com",
            area="Ventas",
        )
        datos.update(overrides)
        return self.directorio.agregar_contacto(**datos)

    def test_agregar_contacto_exitoso_actualiza_indices(self):
        c = self._agregar_contacto_valido()
        self.assertIn(c.telefono, self.directorio.indice_telefonos)
        self.assertIn(c.id, self.directorio.indice_ids)
        self.assertIn(c, self.directorio.indice_areas["Ventas"])
        self.assertEqual(len(self.directorio.contactos), 1)

    def test_agregar_contacto_telefono_duplicado(self):
        self._agregar_contacto_valido(telefono="5511111111")
        with self.assertRaises(ValidationError):
            self._agregar_contacto_valido(telefono="5511111111", correo="otro@empresa.com")

    def test_agregar_contacto_area_invalida(self):
        with self.assertRaises(ValidationError):
            self._agregar_contacto_valido(area="Marketing")

    def test_agregar_contacto_invalido_no_consume_id(self):
        # Un intento fallido no debe generar huecos en la numeración.
        with self.assertRaises(ValidationError):
            self._agregar_contacto_valido(telefono="123")  # teléfono inválido
        c = self._agregar_contacto_valido()
        self.assertEqual(c.id, 1)

    def test_buscar_por_telefono(self):
        c = self._agregar_contacto_valido()
        self.assertEqual(self.directorio.buscar_por_telefono(c.telefono), c)
        self.assertIsNone(self.directorio.buscar_por_telefono("0000000000"))

    def test_buscar_por_id(self):
        c = self._agregar_contacto_valido()
        self.assertEqual(self.directorio.buscar_por_id(c.id), c)
        self.assertIsNone(self.directorio.buscar_por_id(999))

    def test_buscar_por_area(self):
        self._agregar_contacto_valido(nombre="Ana García", telefono="5511111111")
        self._agregar_contacto_valido(nombre="Beto López", telefono="5522222222")
        self._agregar_contacto_valido(nombre="Caro Ruiz", telefono="5533333333", area="Finanzas")
        resultados = self.directorio.buscar_por_area("Ventas")
        self.assertEqual(len(resultados), 2)
        self.assertEqual(self.directorio.buscar_por_area("Finanzas")[0].nombre, "Caro Ruiz")

    def test_eliminar_contacto_por_id_mantiene_consistencia(self):
        c = self._agregar_contacto_valido()
        eliminado = self.directorio.eliminar_contacto(id_contacto=c.id)
        self.assertTrue(eliminado)
        self.assertNotIn(c.id, self.directorio.indice_ids)
        self.assertNotIn(c.telefono, self.directorio.indice_telefonos)
        self.assertNotIn(c, self.directorio.indice_areas.get("Ventas", []))
        self.assertEqual(self.directorio.contactos, [])

    def test_eliminar_contacto_por_telefono(self):
        c = self._agregar_contacto_valido()
        self.assertTrue(self.directorio.eliminar_contacto(telefono=c.telefono))

    def test_eliminar_contacto_inexistente_devuelve_false(self):
        self.assertFalse(self.directorio.eliminar_contacto(id_contacto=999))

    def test_eliminar_sin_criterio_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.directorio.eliminar_contacto()

    def test_mostrar_contactos_orden_alfabetico(self):
        self._agregar_contacto_valido(nombre="Zoe Vargas", telefono="5511111111")
        self._agregar_contacto_valido(nombre="Ana García", telefono="5522222222")
        nombres = [c.nombre for c in self.directorio.mostrar_contactos()]
        self.assertEqual(nombres, ["Ana García", "Zoe Vargas"])

    def test_agregar_area_nueva(self):
        self.directorio.agregar_area("Marketing")
        self.assertIn("Marketing", self.directorio.areas)

    def test_agregar_area_duplicada_lanza_error(self):
        with self.assertRaises(ValidationError):
            self.directorio.agregar_area("Ventas")

    def test_persistencia_guardar_y_recargar_json(self):
        self._agregar_contacto_valido(nombre="Ana García", telefono="5511111111")
        nuevo_directorio = Directorio(ruta_datos=self.ruta_temporal, formato="json")
        self.assertEqual(len(nuevo_directorio.contactos), 1)
        self.assertEqual(nuevo_directorio.buscar_por_telefono("5511111111").nombre, "Ana García")

    def test_persistencia_siguiente_id_continua_tras_recarga(self):
        self._agregar_contacto_valido(nombre="Ana García", telefono="5511111111")
        nuevo_directorio = Directorio(ruta_datos=self.ruta_temporal, formato="json")
        c2 = nuevo_directorio.agregar_contacto(
            nombre="Beto López",
            telefono="5522222222",
            fecha_nacimiento="1992-01-01",
            correo="beto@empresa.com",
            area="Ventas",
        )
        self.assertEqual(c2.id, 2)

    def test_persistencia_csv(self):
        ruta_csv = self.ruta_temporal.replace(".json", ".csv")
        try:
            directorio_csv = Directorio(ruta_datos=ruta_csv, formato="csv")
            directorio_csv.agregar_contacto(
                nombre="Ana García",
                telefono="5511111111",
                fecha_nacimiento="1995-03-20",
                correo="ana@empresa.com",
                area="Ventas",
            )
            with open(ruta_csv, newline="", encoding="utf-8") as f:
                filas = list(csv.DictReader(f))
            self.assertEqual(len(filas), 1)
            self.assertEqual(filas[0]["nombre"], "Ana García")

            recargado = Directorio(ruta_datos=ruta_csv, formato="csv")
            self.assertEqual(len(recargado.contactos), 1)
        finally:
            if os.path.exists(ruta_csv):
                os.remove(ruta_csv)

    def test_cargar_datos_omite_registros_corruptos(self):
        registros = [
            {
                "id": 1,
                "nombre": "Ana García",
                "telefono": "5511111111",
                "fecha_nacimiento": "1995-03-20",
                "correo": "ana@empresa.com",
                "area": "Ventas",
            },
            {
                "id": 2,
                "nombre": "X",  # nombre inválido: se debe omitir
                "telefono": "5522222222",
                "fecha_nacimiento": "1995-03-20",
                "correo": "correo-invalido",
                "area": "Ventas",
            },
        ]
        with open(self.ruta_temporal, "w", encoding="utf-8") as f:
            json.dump(registros, f)

        directorio = Directorio(ruta_datos=self.ruta_temporal, formato="json")
        self.assertEqual(len(directorio.contactos), 1)
        self.assertEqual(directorio.contactos[0].nombre, "Ana García")


if __name__ == "__main__":
    unittest.main(verbosity=2)
