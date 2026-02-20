import { expect, test, beforeAll, afterAll } from "@rstest/core";
import { render, screen, waitFor } from "@testing-library/react";
import App from "../src/App";

const originalFetch = global.fetch;

beforeAll(() => {
	global.fetch = (() =>
		Promise.resolve({
			json: () => Promise.resolve({ message: "Mocked Backend" }),
		})) as any;
});

afterAll(() => {
	global.fetch = originalFetch;
});

test("renders the main page", async () => {
	const testMessage = "Rsbuild with React";
	render(<App />);
	expect(screen.getByText(testMessage)).toBeInTheDocument();
	await waitFor(() => {
		expect(screen.getByText(/Mocked Backend/)).toBeInTheDocument();
	});
});
