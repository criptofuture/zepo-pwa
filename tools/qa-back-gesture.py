#!/usr/bin/env python3
"""
CANDADO del gesto atras (regresion real, 26-jul-2026).

Sintoma que evita: abres una pantalla (Wrapped, Metas...), haces el gesto atras y en vez
de cerrarla SE SALE DE LA APP. Causa: el gesto atras se mantiene con DOS listas escritas
a mano en index.html y una pantalla nueva se olvida en una (o en las dos).

Este test no revisa comportamiento: revisa que NINGUNA pantalla quede huerfana. Cada flag
de estado `<algo>Open` tiene que estar en:
  1. la cadena de `popstate`      -> que el atras la cierre
  2. la lista de `$watch`         -> que al abrirla se meta una entrada al historial
...o estar EXENTA aqui abajo con su motivo escrito.

Anadir una pantalla nueva sin registrarla rompe este test. Ese es el punto.
Sale 1 si falla.
"""
import re, sys, os

PWA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PWA, 'index.html')

# Exentos: NO son pantallas propias, viven dentro de otra que si esta cubierta.
# Para eximir algo nuevo hay que escribir el motivo aqui (es deliberado que cueste).
EXENTOS = {
    'tabMapOpen': 'panel de columnas DENTRO de la hoja de importar (importOpen ya la cubre)',
    'savingsBreakdownOpen': 'acordeon inline dentro de la pestana Patrimonio, no tapa la pantalla',
}

# Exentos SOLO de empujar historial, pero OBLIGADOS a estar en la cadena. Son cosas que se
# cierran solas al usarlas (elegir una opcion); empujar historial les dejaria un "atras"
# sobrante. Faltar en la cadena si es grave y aqui no se perdona.
EXENTOS_WATCH = {
    'catDropdownOpen': 'desplegable que se cierra al elegir categoria; la cadena repone la entrada',
}


def main():
    src = open(SRC, encoding='utf-8').read()

    # 1. Las pantallas declaradas en el estado Alpine.
    flags = set(re.findall(r'^\s{4}(\w+Open):\s*(?:false|true)', src, re.M))
    if len(flags) < 15:
        print(f'[FALLA] solo encontre {len(flags)} flags *Open: cambio el formato del estado,'
              ' este test se quedo ciego -> arreglar el regex')
        return False

    # 2. La cadena del gesto atras.
    m = re.search(r"addEventListener\('popstate'.*?finally \{ this\._navPopping = false; \}",
                  src, re.S)
    if not m:
        print('[FALLA] no encontre el handler de popstate -> este test se quedo ciego')
        return False
    cadena = set(re.findall(r'this\.(\w+Open)', m.group(0)))

    # 3. La lista que empuja historial al abrir.
    m2 = re.search(r"\n\s*\[('sheetOpen'.*?)\]\.forEach", src, re.S)
    if not m2:
        print('[FALLA] no encontre la lista de $watch -> este test se quedo ciego')
        return False
    watchers = set(re.findall(r"'(\w+Open)'", m2.group(1)))

    problemas = []
    for f in sorted(flags):
        if f in EXENTOS:
            continue
        falta = []
        if f not in cadena:
            falta.append('la cadena de popstate (el atras NO la cierra -> SALE DE LA APP)')
        if f not in watchers and f not in EXENTOS_WATCH:
            falta.append('la lista de $watch (no empuja historial -> el atras se come otra cosa)')
        if falta:
            problemas.append((f, falta))

    # Exento que ya no existe = limpiar la lista de arriba.
    huerfanos = [e for e in list(EXENTOS) + list(EXENTOS_WATCH) if e not in flags]

    print('\n=== Candado del gesto atras ===')
    print(f'  pantallas revisadas: {len(flags)}  ({len(EXENTOS)} exentas)')
    for f, falta in problemas:
        print(f'  [FALLA] "{f}" no esta en: ' + ' NI en '.join(falta))
    for h in huerfanos:
        print(f'  [FALLA] "{h}" esta exento pero ya no existe -> sacalo de EXENTOS')
    if not problemas and not huerfanos:
        print('  [PASS] toda pantalla se cierra con el gesto atras')
        return True
    print('\n  Arreglo: anadir el flag a las DOS listas de index.html (busca "popstate"),'
          '\n  o eximirlo en EXENTOS de este archivo con el motivo.')
    return False


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
