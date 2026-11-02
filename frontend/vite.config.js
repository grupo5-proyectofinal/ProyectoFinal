import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// En docker compose el backend es otro contenedor: API_URL lo apunta (por defecto, local).
const API_URL = process.env.API_URL ?? 'http://127.0.0.1:8000';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) => filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	server: {
		// Los volúmenes de Docker en Windows no emiten eventos de archivos: polling opcional.
		watch: process.env.VITE_USE_POLLING ? { usePolling: true, interval: 300 } : undefined,
		proxy: {
			'/api': API_URL,
			'/media': API_URL
		}
	}
});
