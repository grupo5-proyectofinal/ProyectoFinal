import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const RAIZ = new URL('../src/', import.meta.url);

function fuente(ruta) {
	return readFileSync(new URL(ruta, RAIZ), 'utf8');
}

const LAYOUT = fuente('routes/+layout.svelte');

// --- DW-5.1/DW-5.2/DW-5.3: identidad y menú de sesión ---
// Sin DOM harness, estos pines de cableado son la única guarda ejecutable de los
// handlers del header. Se conservan solo los que fallan si se rompe la sesión, la
// identidad o el patrón accesible del menú; los pines de clases/estilos/textos y
// las repeticiones de helpers puros (ya cubiertos en unit/admin) se retiraron en
// la limpieza: no detectaban defectos de comportamiento.

test('DW-5.1/DW-5.2: la identidad vive en escritorio y móvil, y solo con sesión', () => {
	// El snippet de identidad se renderiza en la sesión de escritorio y en el menú móvil.
	assert.equal(LAYOUT.match(/\{@render identidad\(\)\}/g)?.length, 2);
	assert.equal(LAYOUT.match(/\{#if session\.access\}/g)?.length, 2);
	// PODA (P1, rediseño): el pin del monograma/foto (`iniciales(nombreSesion)` inline)
	// quedó obsoleto: ahora lo encapsula la primitiva <Avatar>. El guard de "identidad en
	// ambos menús y solo con sesión" se conserva con los asserts estructurales de arriba.
});

test('DW-5.3: Escape cierra el menú de usuario y devuelve el foco al trigger', () => {
	// Guard clause: solo Escape dispara el cierre.
	assert.match(LAYOUT, /if \(event\.key !== 'Escape'\) return;/);
	assert.match(LAYOUT, /menuUsuarioAbierto = false;\s*botonUsuario\?\.focus\(\)/);
	// Click afuera cierra el menú y el patrón aria acompaña al trigger.
	assert.match(LAYOUT, /!contenedorUsuario\?\.contains\(event\.target\)/);
	assert.match(LAYOUT, /aria-expanded={menuUsuarioAbierto}/);
	assert.match(LAYOUT, /aria-controls="menu-usuario"/);
	assert.match(LAYOUT, /hidden={!menuUsuarioAbierto}/);
	// Sin nombre (cargando) el botón conserva nombre accesible.
	assert.match(LAYOUT, /aria-label={nombreSesion \? undefined : 'Menú de cuenta'}/);
});

test('DW-5.1: cerrar sesión limpia el estado y vuelve al inicio', () => {
	assert.match(
		LAYOUT,
		/function cerrarSesion\(\)[\s\S]{0,120}?logout\(\);[\s\S]{0,120}?goto\(resolve\('\/'\)\)/
	);
});

test('DW-5.3: el menú móvil conserva su patrón accesible', () => {
	assert.match(LAYOUT, /aria-expanded={menuAbierto}/);
	assert.match(LAYOUT, /aria-controls="menu-movil"/);
	// Escape también cierra el menú móvil y devuelve el foco.
	assert.match(LAYOUT, /menuAbierto = false;\s*botonMenu\?\.focus\(\)/);
});
