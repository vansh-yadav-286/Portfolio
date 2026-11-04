import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './' // relative paths, so the build also works from a sub-folder (e.g. GitHub Pages)
});
