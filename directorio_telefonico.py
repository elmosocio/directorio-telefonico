"""
Directorio telefónico con clases, listas y diccionarios
=========================================================

Sistema de gestión de contactos implementado con Programación Orientada
a Objetos. Provee:

- ``Contacto``: entidad de dominio con validación de datos por diseño
  (las validaciones se aplican tanto en la construcción como en cualquier
  reasignación posterior de un atributo, mediante propiedades).
- ``Directorio``: colección de contactos con acceso O(1) por teléfono,
  por ID y por área mediante diccionarios de índice, y persistencia en
  JSON o CSV.
- ``InterfazUsuario``: capa de presentación por consola, desacoplada de
  la lógica de negocio (principio de responsabilidad única).

Autor: (completar con tu nombre)
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
from datetime import date, datetime
from typing import Dict, List, Optional, Set

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Se lanza cuando un dato de contacto no cumple las reglas de negocio."""


# ---------------------------------------------------------------------------
# Contacto
# ---------------------------------------------------------------------------
class Contacto:
    """Representa un contacto individual del directorio telefónico.

    Los atributos se exponen como propiedades para que cualquier
    reasignación posterior a la construcción (``contacto.telefono = "..."``)
    quede sujeta a las mismas reglas de validación que el constructor,
    garantizando que el objeto nunca se encuentre en un estado inválido.

    Attributes:
        id (int): Identificador único, entero positivo.
        nombre (str): Nombre completo (mínimo 2 palabras, 5 caracteres).
        telefono (str): Cadena de exactamente 10 dígitos numéricos.
        fecha_nacimiento (str): Fecha en formato ISO 8601 (YYYY-MM-DD).
        correo (str): Correo electrónico con formato válido.
        area (str): Área organizacional a la que pertenece el contacto.
    """

    # Patrón práctico para validar correos (subconjunto realista de RFC 5322;
    # la gramática completa de RFC 5322 es extremadamente permisiva y poco
    # útil en la práctica, por lo que se usa el patrón que emplean la
    # mayoría de frameworks de producción, p. ej. el <input type="email">
    # de HTML5 o el validador de Django).
    _PATRON_CORREO = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
        r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
        r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
    )
    _PATRON_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*$")
    _FECHA_MINIMA = date(1925, 1, 1)

    def __init__(
        self,
        id: int,
        nombre: str,
        telefono: str,
        fecha_nacimiento: str,
        correo: str,
        area: str,
        areas_validas: Optional[Set[str]] = None,
    ) -> None:
        """Construye y valida un ``Contacto``.

        Args:
            id: Identificador único positivo.
            nombre: Nombre completo del contacto.
            telefono: Teléfono de 10 dígitos.
            fecha_nacimiento: Fecha en formato ISO 8601.
            correo: Correo electrónico.
            area: Área organizacional.
            areas_validas: Conjunto de áreas permitidas contra el cual
                validar ``area``. Si es ``None`` solo se valida que el
                área sea una cadena no vacía (útil para deserialización
                donde el catálogo de áreas aún no está disponible).

        Raises:
            ValidationError: Si cualquier campo no cumple sus reglas.
        """
        self.id = id
        self._areas_validas = areas_validas
        self.nombre = nombre
        self.telefono = telefono
        self.fecha_nacimiento = fecha_nacimiento
        self.correo = correo
        self.area = area

    # -- id ------------------------------------------------------------
    @property
    def id(self) -> int:
        return self._id

    @id.setter
    def id(self, valor: int) -> None:
        if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
            raise ValidationError("El ID debe ser un entero positivo.")
        self._id = valor

    # -- nombre ----------------------------------------------------------
    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        Contacto.validar_nombre(valor)
        self._nombre = valor.strip()

    @staticmethod
    def validar_nombre(nombre: str) -> bool:
        """Valida que ``nombre`` tenga al menos 2 palabras, 5 caracteres
        y solo contenga letras y espacios."""
        if not isinstance(nombre, str):
            raise ValidationError("El nombre debe ser una cadena de texto.")
        limpio = nombre.strip()
        if len(limpio) < 5:
            raise ValidationError(
                f"El nombre debe tener al menos 5 caracteres (recibidos: {len(limpio)})."
            )
        if len(limpio.split()) < 2:
            raise ValidationError("El nombre debe incluir al menos 2 palabras (nombre y apellido).")
        if not Contacto._PATRON_NOMBRE.match(limpio):
            raise ValidationError("El nombre solo puede contener letras y espacios.")
        return True

    # -- telefono --------------------------------------------------------
    @property
    def telefono(self) -> str:
        return self._telefono

    @telefono.setter
    def telefono(self, valor: str) -> None:
        Contacto.validar_telefono(valor)
        self._telefono = valor

    @staticmethod
    def validar_telefono(telefono: str) -> bool:
        """Valida que ``telefono`` sean exactamente 10 dígitos numéricos."""
        if not isinstance(telefono, str):
            raise ValidationError("El teléfono debe ser una cadena de texto.")
        if len(telefono) != 10:
            raise ValidationError(
                f"El teléfono debe tener exactamente 10 dígitos (recibidos: {len(telefono)})."
            )
        if not telefono.isdigit():
            raise ValidationError("El teléfono solo puede contener dígitos (0-9).")
        return True

    # -- correo ------------------------------------------------------------
    @property
    def correo(self) -> str:
        return self._correo

    @correo.setter
    def correo(self, valor: str) -> None:
        Contacto.validar_correo(valor)
        self._correo = valor.strip()

    @staticmethod
    def validar_correo(correo: str) -> bool:
        """Valida el formato ``usuario@dominio.extension``."""
        if not isinstance(correo, str) or not Contacto._PATRON_CORREO.match(correo.strip()):
            raise ValidationError(
                f"El correo '{correo}' no tiene un formato válido (usuario@dominio.extension)."
            )
        return True

    # -- fecha_nacimiento --------------------------------------------------
    @property
    def fecha_nacimiento(self) -> str:
        return self._fecha_nacimiento

    @fecha_nacimiento.setter
    def fecha_nacimiento(self, valor: str) -> None:
        Contacto.validar_fecha_nacimiento(valor)
        self._fecha_nacimiento = valor

    @staticmethod
    def validar_fecha_nacimiento(fecha_str: str) -> bool:
        """Valida formato ISO 8601, calendario real y rango [1925-01-01, hoy]."""
        if not isinstance(fecha_str, str):
            raise ValidationError("La fecha de nacimiento debe ser una cadena de texto.")
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(
                "La fecha debe tener formato ISO 8601 (YYYY-MM-DD) "
                "y corresponder a un día calendario válido."
            )
        hoy = date.today()
        if fecha < Contacto._FECHA_MINIMA or fecha > hoy:
            raise ValidationError(
                f"La fecha debe estar entre {Contacto._FECHA_MINIMA.isoformat()} "
                f"y {hoy.isoformat()}."
            )
        return True

    # -- area --------------------------------------------------------------
    @property
    def area(self) -> str:
        return self._area

    @area.setter
    def area(self, valor: str) -> None:
        Contacto.validar_area(valor, self._areas_validas)
        self._area = valor.strip()

    @staticmethod
    def validar_area(area: str, areas_validas: Optional[Set[str]] = None) -> bool:
        """Valida que ``area`` sea una cadena no vacía y, si se provee
        ``areas_validas``, que pertenezca al catálogo permitido."""
        if not isinstance(area, str) or not area.strip():
            raise ValidationError("El área no puede estar vacía.")
        if areas_validas is not None and area not in areas_validas:
            raise ValidationError(
                f"El área '{area}' no está registrada como área organizacional válida."
            )
        return True

    # -- representación y serialización ------------------------------------
    def __str__(self) -> str:
        return f"ID: {self.id} | {self.nombre} | ☎ {self.telefono} | {self.area}"

    def __repr__(self) -> str:
        return (
            f"Contacto(id={self.id}, nombre={self.nombre!r}, "
            f"telefono={self.telefono!r}, area={self.area!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Contacto):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def to_dict(self) -> dict:
        """Serializa el contacto a un diccionario plano (para JSON/CSV)."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "telefono": self.telefono,
            "fecha_nacimiento": self.fecha_nacimiento,
            "correo": self.correo,
            "area": self.area,
        }

    @classmethod
    def from_dict(cls, datos: dict, areas_validas: Optional[Set[str]] = None) -> "Contacto":
        """Reconstruye un ``Contacto`` a partir de un diccionario (p. ej.
        leído desde JSON o una fila de CSV)."""
        return cls(
            id=int(datos["id"]),
            nombre=datos["nombre"],
            telefono=str(datos["telefono"]),
            fecha_nacimiento=datos["fecha_nacimiento"],
            correo=datos["correo"],
            area=datos["area"],
            areas_validas=areas_validas,
        )


# ---------------------------------------------------------------------------
# Directorio
# ---------------------------------------------------------------------------
class Directorio:
    """Gestiona la colección de contactos: almacenamiento, índices de
    búsqueda O(1), reglas de unicidad y persistencia en disco.

    Attributes:
        contactos (List[Contacto]): Lista maestra de contactos.
        indice_telefonos (Dict[str, Contacto]): Índice teléfono -> contacto.
        indice_ids (Dict[int, Contacto]): Índice id -> contacto.
        indice_areas (Dict[str, List[Contacto]]): Índice área -> contactos.
        areas (Set[str]): Catálogo de áreas organizacionales válidas.
    """

    AREAS_PREDETERMINADAS = {
        "Ventas",
        "Recursos Humanos",
        "Tecnología",
        "Finanzas",
        "Operaciones",
        "Dirección General",
    }

    def __init__(self, ruta_datos: str = "contactos.json", formato: str = "json") -> None:
        """Inicializa un directorio vacío y carga datos existentes si
        ``ruta_datos`` ya existe en disco.

        Args:
            ruta_datos: Ruta del archivo de persistencia.
            formato: ``"json"`` o ``"csv"``.
        """
        if formato.lower() not in ("json", "csv"):
            raise ValueError("El formato de persistencia debe ser 'json' o 'csv'.")

        self.contactos: List[Contacto] = []
        self.indice_telefonos: Dict[str, Contacto] = {}
        self.indice_ids: Dict[int, Contacto] = {}
        self.indice_areas: Dict[str, List[Contacto]] = {}
        self.areas: Set[str] = set(self.AREAS_PREDETERMINADAS)

        self.ruta_datos = ruta_datos
        self.formato = formato.lower()
        self._siguiente_id = 1

        self.cargar_datos()

    # -- gestión de áreas ----------------------------------------------------
    def agregar_area(self, nueva_area: str) -> bool:
        """Registra una nueva área en el catálogo de áreas válidas.

        Raises:
            ValidationError: Si el nombre está vacío o ya existe.
        """
        nueva_area = (nueva_area or "").strip()
        if not nueva_area:
            raise ValidationError("El nombre del área no puede estar vacío.")
        if nueva_area in self.areas:
            raise ValidationError(f"El área '{nueva_area}' ya existe.")
        self.areas.add(nueva_area)
        self.indice_areas.setdefault(nueva_area, [])
        return True

    def seleccionar_area(self) -> str:
        """Presenta un listado numerado de áreas y devuelve la elegida
        por el usuario (entrada interactiva por consola)."""
        areas_ordenadas = sorted(self.areas)
        print("\nÁreas disponibles:")
        for i, area in enumerate(areas_ordenadas, start=1):
            print(f"  {i}. {area}")
        while True:
            seleccion = input("Seleccione el número de área: ").strip()
            if seleccion.isdigit() and 1 <= int(seleccion) <= len(areas_ordenadas):
                return areas_ordenadas[int(seleccion) - 1]
            print("  ✗ Selección inválida. Intente de nuevo.")

    # -- ciclo de vida de contactos -------------------------------------------
    def _generar_id(self) -> int:
        nuevo_id = self._siguiente_id
        self._siguiente_id += 1
        return nuevo_id

    def agregar_contacto(
        self,
        nombre: str,
        telefono: str,
        fecha_nacimiento: str,
        correo: str,
        area: str,
        guardar: bool = True,
    ) -> Contacto:
        """Valida, crea, indexa y persiste un nuevo contacto.

        Los campos se validan *antes* de reservar un ID, de modo que un
        intento fallido no genere huecos en la numeración.

        Raises:
            ValidationError: Si algún campo es inválido, el teléfono ya
                existe, o el área no está en el catálogo.
        """
        Contacto.validar_nombre(nombre)
        Contacto.validar_telefono(telefono)
        Contacto.validar_fecha_nacimiento(fecha_nacimiento)
        Contacto.validar_correo(correo)
        Contacto.validar_area(area, self.areas)

        if telefono in self.indice_telefonos:
            raise ValidationError(f"Ya existe un contacto con el teléfono {telefono}.")

        contacto = Contacto(
            id=self._generar_id(),
            nombre=nombre,
            telefono=telefono,
            fecha_nacimiento=fecha_nacimiento,
            correo=correo,
            area=area,
            areas_validas=self.areas,
        )

        self.contactos.append(contacto)
        self.indice_telefonos[contacto.telefono] = contacto
        self.indice_ids[contacto.id] = contacto
        self.indice_areas.setdefault(contacto.area, []).append(contacto)

        if guardar:
            self.guardar_datos()

        return contacto

    def buscar_por_telefono(self, telefono: str) -> Optional[Contacto]:
        """Búsqueda O(1) por teléfono exacto."""
        return self.indice_telefonos.get(telefono)

    def buscar_por_id(self, id_contacto: int) -> Optional[Contacto]:
        """Búsqueda O(1) por ID."""
        return self.indice_ids.get(id_contacto)

    def buscar_por_area(self, area: str) -> List[Contacto]:
        """Devuelve la lista de contactos de un área (copia defensiva)."""
        return list(self.indice_areas.get(area, []))

    def eliminar_contacto(
        self,
        id_contacto: Optional[int] = None,
        telefono: Optional[str] = None,
        guardar: bool = True,
    ) -> bool:
        """Elimina un contacto por ID o por teléfono, manteniendo la
        consistencia de los tres índices.

        Returns:
            ``True`` si se eliminó un contacto, ``False`` si no se encontró.

        Raises:
            ValueError: Si no se proporciona ni ``id_contacto`` ni ``telefono``.
        """
        if id_contacto is None and telefono is None:
            raise ValueError("Debe proporcionar un ID o un teléfono para eliminar un contacto.")

        contacto = (
            self.indice_ids.get(id_contacto) if id_contacto is not None
            else self.indice_telefonos.get(telefono)
        )
        if contacto is None:
            return False

        self.contactos.remove(contacto)
        self.indice_ids.pop(contacto.id, None)
        self.indice_telefonos.pop(contacto.telefono, None)
        lista_area = self.indice_areas.get(contacto.area, [])
        if contacto in lista_area:
            lista_area.remove(contacto)

        if guardar:
            self.guardar_datos()

        return True

    def mostrar_contactos(self) -> List[Contacto]:
        """Devuelve todos los contactos ordenados alfabéticamente por nombre."""
        return sorted(self.contactos, key=lambda c: c.nombre.lower())

    # -- persistencia ----------------------------------------------------
    def guardar_datos(self, ruta: Optional[str] = None, formato: Optional[str] = None) -> None:
        """Persiste todos los contactos en disco en formato JSON o CSV."""
        ruta = ruta or self.ruta_datos
        formato_efectivo = (formato or self.formato).lower()
        datos = [c.to_dict() for c in self.contactos]

        if formato_efectivo == "json":
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
        elif formato_efectivo == "csv":
            campos = ["id", "nombre", "telefono", "fecha_nacimiento", "correo", "area"]
            with open(ruta, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=campos)
                writer.writeheader()
                writer.writerows(datos)
        else:
            raise ValueError(f"Formato de persistencia no soportado: {formato_efectivo}")

    def cargar_datos(self, ruta: Optional[str] = None, formato: Optional[str] = None) -> None:
        """Carga contactos desde disco (si el archivo existe) y reconstruye
        los índices y el catálogo de áreas. Los registros corruptos se
        omiten con una advertencia, sin detener la carga completa."""
        ruta = ruta or self.ruta_datos
        formato_efectivo = (formato or self.formato).lower()

        if not os.path.exists(ruta):
            return

        registros: List[dict] = []
        try:
            if formato_efectivo == "json":
                with open(ruta, "r", encoding="utf-8") as f:
                    registros = json.load(f)
            elif formato_efectivo == "csv":
                with open(ruta, "r", encoding="utf-8", newline="") as f:
                    registros = list(csv.DictReader(f))
            else:
                raise ValueError(f"Formato de persistencia no soportado: {formato_efectivo}")
        except (json.JSONDecodeError, csv.Error, OSError) as e:
            raise RuntimeError(f"Error al leer el archivo de datos '{ruta}': {e}") from e

        max_id = 0
        for registro in registros:
            try:
                area = registro["area"]
                self.areas.add(area)
                contacto = Contacto.from_dict(registro, areas_validas=self.areas)

                if contacto.telefono in self.indice_telefonos:
                    logger.warning(
                        "Teléfono duplicado '%s' en '%s'; registro omitido.",
                        contacto.telefono, ruta,
                    )
                    continue

                self.contactos.append(contacto)
                self.indice_ids[contacto.id] = contacto
                self.indice_telefonos[contacto.telefono] = contacto
                self.indice_areas.setdefault(contacto.area, []).append(contacto)
                max_id = max(max_id, contacto.id)
            except (ValidationError, KeyError, ValueError) as e:
                logger.warning("Registro inválido omitido en '%s': %s", ruta, e)

        self._siguiente_id = max_id + 1


# ---------------------------------------------------------------------------
# InterfazUsuario
# ---------------------------------------------------------------------------
class InterfazUsuario:
    """Capa de presentación por consola. No contiene lógica de negocio:
    delega toda operación sobre los datos al ``Directorio`` inyectado."""

    def __init__(self, directorio: Directorio) -> None:
        self.directorio = directorio

    # -- navegación --------------------------------------------------------
    def mostrar_menu_principal(self) -> None:
        print("\n" + "=" * 45)
        print("   DIRECTORIO TELEFÓNICO - MENÚ PRINCIPAL")
        print("=" * 45)
        print("1. Agregar contacto")
        print("2. Buscar contacto por teléfono")
        print("3. Buscar contacto por ID")
        print("4. Buscar contactos por área")
        print("5. Eliminar contacto")
        print("6. Mostrar todos los contactos")
        print("7. Agregar nueva área")
        print("8. Salir")
        print("=" * 45)

    def ejecutar(self) -> None:
        """Bucle principal de la aplicación."""
        acciones = {
            1: self._flujo_agregar_contacto,
            2: self._flujo_buscar_telefono,
            3: self._flujo_buscar_id,
            4: self._flujo_buscar_area,
            5: self._flujo_eliminar_contacto,
            6: self._flujo_mostrar_contactos,
            7: self._flujo_agregar_area,
        }
        print("Bienvenido al Directorio Telefónico.")
        while True:
            self.mostrar_menu_principal()
            opcion = self.leer_opcion(1, 8)
            if opcion == 8:
                print("\n¡Hasta luego!")
                break
            acciones[opcion]()

    # -- entrada -------------------------------------------------------
    def leer_opcion(self, minimo: int = 1, maximo: int = 8) -> int:
        """Lee y valida una opción numérica del menú dentro de un rango."""
        while True:
            opcion = input(f"Seleccione una opción ({minimo}-{maximo}): ").strip()
            if opcion.isdigit() and minimo <= int(opcion) <= maximo:
                return int(opcion)
            print(f"  ✗ Opción inválida. Ingrese un número entre {minimo} y {maximo}.")

    def leer_dato(self, mensaje: str, validador=None, reintentos: int = 3) -> str:
        """Lee un dato de texto, aplicando ``validador`` (una función que
        lanza ``ValidationError``) hasta ``reintentos`` veces.

        Raises:
            ValidationError: Si se agotan los reintentos sin éxito.
        """
        intentos = 0
        while intentos < reintentos:
            valor = input(mensaje).strip()
            if validador is None:
                return valor
            try:
                validador(valor)
                return valor
            except ValidationError as e:
                intentos += 1
                restantes = reintentos - intentos
                print(f"  ✗ {e}" + (f" ({restantes} intento(s) restante(s))" if restantes else ""))
        raise ValidationError(f"Se alcanzó el número máximo de reintentos ({reintentos}).")

    # -- flujos de cada opción del menú -------------------------------------
    def _flujo_agregar_contacto(self) -> None:
        print("\n--- Agregar nuevo contacto ---")
        try:
            nombre = self.leer_dato("Nombre completo: ", Contacto.validar_nombre)
            telefono = self.leer_dato("Teléfono (10 dígitos): ", Contacto.validar_telefono)
            fecha = self.leer_dato(
                "Fecha de nacimiento (YYYY-MM-DD): ", Contacto.validar_fecha_nacimiento
            )
            correo = self.leer_dato("Correo electrónico: ", Contacto.validar_correo)
            area = self.directorio.seleccionar_area()
            contacto = self.directorio.agregar_contacto(nombre, telefono, fecha, correo, area)
            print(f"\n✓ Contacto agregado exitosamente:\n  {contacto}")
        except ValidationError as e:
            print(f"\n✗ No se pudo agregar el contacto: {e}")

    def _flujo_buscar_telefono(self) -> None:
        telefono = input("\nIngrese el teléfono a buscar: ").strip()
        contacto = self.directorio.buscar_por_telefono(telefono)
        print(f"\n{contacto}" if contacto else "\nNo se encontró ningún contacto con ese teléfono.")

    def _flujo_buscar_id(self) -> None:
        id_str = input("\nIngrese el ID a buscar: ").strip()
        if not id_str.isdigit():
            print("  ✗ El ID debe ser un número entero.")
            return
        contacto = self.directorio.buscar_por_id(int(id_str))
        print(f"\n{contacto}" if contacto else "\nNo se encontró ningún contacto con ese ID.")

    def _flujo_buscar_area(self) -> None:
        area = self.directorio.seleccionar_area()
        resultados = sorted(self.directorio.buscar_por_area(area), key=lambda c: c.nombre.lower())
        if not resultados:
            print(f"\nNo hay contactos registrados en el área '{area}'.")
            return
        print(f"\nContactos en '{area}':")
        for c in resultados:
            print(f"  {c}")

    def _flujo_eliminar_contacto(self) -> None:
        print("\n--- Eliminar contacto ---")
        print("1. Por ID")
        print("2. Por teléfono")
        modo = self.leer_opcion(1, 2)
        if modo == 1:
            id_str = input("ID del contacto a eliminar: ").strip()
            if not id_str.isdigit():
                print("  ✗ ID inválido.")
                return
            eliminado = self.directorio.eliminar_contacto(id_contacto=int(id_str))
        else:
            telefono = input("Teléfono del contacto a eliminar: ").strip()
            eliminado = self.directorio.eliminar_contacto(telefono=telefono)
        if eliminado:
            print("\n✓ Contacto eliminado.")
        else:
            print("\n✗ No se encontró el contacto especificado.")

    def _flujo_mostrar_contactos(self) -> None:
        contactos = self.directorio.mostrar_contactos()
        if not contactos:
            print("\nEl directorio está vacío.")
            return
        print(f"\n--- Contactos registrados ({len(contactos)}) ---")
        for c in contactos:
            print(f"  {c}")

    def _flujo_agregar_area(self) -> None:
        nueva_area = input("\nNombre de la nueva área: ").strip()
        try:
            self.directorio.agregar_area(nueva_area)
            print(f"✓ Área '{nueva_area}' agregada correctamente.")
        except ValidationError as e:
            print(f"✗ {e}")


def main() -> None:
    directorio = Directorio(ruta_datos="contactos.json", formato="json")
    interfaz = InterfazUsuario(directorio)
    interfaz.ejecutar()


if __name__ == "__main__":
    main()
