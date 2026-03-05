import { useEffect, useState } from "react";
import "./App.css";
import Card from "./comp/Card";

const App = () => {
	const [status, setStatus] = useState<string>("Loading...");

	// useEffect(() => {
	// 	fetch("/api/health")
	// 		.then((res) => res.json())
	// 		.then((data) => setStatus(data.message))
	// 		.catch((err) => {
	// 			console.error("Error fetching health status:", err);
	// 			setStatus("Error connecting to backend");
	// 		});
	// }, []);

	return (
		<Card>
			<h1>Rsbuild with React</h1>
			<p>
				Backend Status: <strong>{status}</strong>
			</p>
			<p>Start building amazing things with Rsbuild.</p>
		</Card>
	);
};

export default App;
