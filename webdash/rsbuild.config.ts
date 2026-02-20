import { defineConfig } from "@rsbuild/core";
import { pluginReact } from "@rsbuild/plugin-react";

// Docs: https://rsbuild.rs/config/
export default defineConfig({
	plugins: [pluginReact()],
	server: {
		proxy: {
			"/api": "http://127.0.0.1:5000",
		},
	},
});
