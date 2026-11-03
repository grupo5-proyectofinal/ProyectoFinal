import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

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
		proxy: {
			// En Docker el backend es otro contenedor (`API_URL=http://backend:8000`).
			'/api': process.env.API_URL || 'http://127.0.0.1:8000',
			'/media': process.env.API_URL || 'http://127.0.0.1:8000'
		}
	}
});
