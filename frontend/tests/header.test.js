import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { nombreUsuario } from '../src/lib/admin.js';
import { TONOS, tonoNombre } from '../src/lib/estados.js';
import { iniciales } from '../src/lib/formato.js';

const RAIZ = new URL('../src/', import.meta.url);

function fuente(ruta) {
	return readFileSync(new URL(ruta, RAIZ), 'utf8');
}

const LAYOUT = fuente('routes/+layout.svelte');

// --- DW-5.1: identidad en escritorio y móvil, menú de sesión ---

test('DW-5.1: el header arma la identidad en escritorio y móvil', () => {
	// El snippet de identidad se renderiza en la sesión de escritorio y en el menú móvil.
	assert.equal(LAYOUT.match(/\{@render identidad\(\)\}/g)?.length, 2);
	assert.match(LAYOUT, /class="usuario"/);
	assert.match(LAYOUT, /class="usuario__boton"/);
	assert.match(LAYOUT, /class="menu-movil__identidad"/);
	// Avatar con foto o monograma + nombre visible del usuario de sesión.
	assert.match(LAYOUT, /session\.user\?\.foto/);
	assert.match(LAYOUT, /src={session\.user\.foto}/);
	assert.match(LAYOUT, /iniciales\(nombreSesion\)/);
	assert.match(LAYOUT, /nombreUsuario\(session\.user\)/);
});

test('DW-5.1: el menú de sesión navega a perfil y cierra sesión', () => {
	assert.match(LAYOUT, /id="menu-usuario"/);
	assert.match(LAYOUT, /href={resolve\('\/perfil'\)}/);
	assert.match(LAYOUT, /onclick=\{\(\) => \(menuUsuarioAbierto = false\)\}/);
	// Cerrar sesión limpia el estado y vuelve al inicio.
	assert.match(LAYOUT, /function cerrarSesion\(\)/);
	assert.match(LAYOUT, /logout\(\)/);
	assert.match(LAYOUT, /goto\(resolve\('\/'\)\)/);
});

test('DW-5.1: el nombre visible es nombre + apellido y el tono es estable por username', () => {
	assert.equal(
		nombreUsuario({ first_name: 'Ana', last_name: 'Perez', username: 'ana' }),
		'Ana Perez'
	);
	assert.equal(nombreUsuario({ first_name: 'Ana', last_name: '', username: 'ana' }), 'Ana');
	assert.equal(tonoNombre('ana'), tonoNombre('ana'));
	assert.ok(TONOS.includes(tonoNombre('ana')));
	// El tono sale del username (estable ante ediciones del nombre), no del nombre visible.
	assert.match(LAYOUT, /tonoNombre\(session\.user\.username\)/);
});

// --- DW-5.2: monograma sin foto, identidad solo con sesión ---

test('DW-5.2: sin foto el avatar es el monograma con tono', () => {
	assert.match(LAYOUT, /\{#if session\.user\?\.foto\}/);
	assert.match(LAYOUT, /src={session\.user\.foto} alt="" \/>/);
	assert.match(
		LAYOUT,
		/\{:else\}[\s\S]*?class="avatar avatar--sm \{tonoSesion\}" aria-hidden="true">\{iniciales\(nombreSesion\)\}/
	);
});

test('DW-5.2: sin sesión no aparece la identidad y quedan los botones actuales', () => {
	// La identidad vive dentro del gate de sesión, en escritorio y en móvil.
	assert.equal(LAYOUT.match(/\{#if session\.access\}/g)?.length, 2);
	assert.match(LAYOUT, />Ingresar</);
	assert.match(LAYOUT, />Crear cuenta</);
	// Mientras loadMe resuelve (user null) el monograma cae a "?" y no hay nombre.
	assert.equal(iniciales(nombreUsuario(null)), '?');
	assert.equal(iniciales(nombreUsuario({ first_name: '', last_name: '', username: '' })), '?');
});

test('DW-5.2: nombre vacío cae al username y el monograma nunca queda vacío', () => {
	assert.equal(nombreUsuario({ first_name: '', last_name: '', username: 'ana' }), 'ana');
	assert.equal(nombreUsuario({ username: '' }), '');
	assert.equal(nombreUsuario(null), '');
	assert.equal(iniciales(nombreUsuario({ first_name: 'Ana', last_name: 'Perez' })), 'AP');
	assert.equal(iniciales(nombreUsuario({ username: 'ana' })), 'A');
	assert.equal(iniciales(nombreUsuario(null)), '?');
});

// --- DW-5.3: Escape, foco y patrón accesible del header ---

test('DW-5.3: Escape cierra el menú y devuelve el foco al trigger', () => {
	assert.match(LAYOUT, /<svelte:window onkeydown={alTeclear}/);
	// Guard clause: solo Escape dispara el cierre.
	assert.match(LAYOUT, /if \(event\.key !== 'Escape'\) return;/);
	// Cierra el menú de usuario y devuelve el foco; el menú móvil conserva su patrón.
	assert.match(LAYOUT, /menuUsuarioAbierto = false;\s*botonUsuario\?\.focus\(\);/);
	assert.match(LAYOUT, /menuAbierto = false;\s*botonMenu\?\.focus\(\);/);
	// Cambio de ruta: cierra ambos menús.
	assert.match(LAYOUT, /void page\.url\.pathname;[\s\S]*?menuUsuarioAbierto = false;/);
});

test('DW-5.3: click afuera cierra el menú y el patrón aria acompaña al trigger', () => {
	assert.match(LAYOUT, /<svelte:window onkeydown={alTeclear} onclick={alClicFuera}/);
	assert.match(LAYOUT, /!contenedorUsuario\?\.contains\(event\.target\)/);
	assert.match(LAYOUT, /aria-expanded={menuUsuarioAbierto}/);
	assert.match(LAYOUT, /aria-controls="menu-usuario"/);
	assert.match(LAYOUT, /hidden={!menuUsuarioAbierto}/);
	// Sin nombre (cargando) el botón conserva nombre accesible.
	assert.match(LAYOUT, /aria-label={nombreSesion \? undefined : 'Menú de cuenta'}/);
});

// --- Bordes más allá de los DW ---

test('header: el nombre no se imprime vacío y la foto es decorativa', () => {
	assert.match(LAYOUT, /\{#if nombreSesion\}[\s\S]*?\{nombreSesion\}/);
	assert.match(LAYOUT, /alt=""/);
});

test('header: el patrón del menú móvil queda intacto', () => {
	assert.match(LAYOUT, /aria-controls="menu-movil"/);
	assert.match(LAYOUT, /aria-expanded={menuAbierto}/);
	assert.match(LAYOUT, /id="menu-movil"/);
});
