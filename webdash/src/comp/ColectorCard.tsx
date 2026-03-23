import type React from "react";
import { useEffect, useState } from "react";
import Card from "./Card";

const ColectorCard: React.FC = () => {
	const [counter, setCounter] = useState<number>(0);
	const [directory, setDirectory] = useState<string>("");
	const [classification, setClassification] = useState<string>("class");

	const [status, setStatus] = useState<string | null>(null);

	const notify = (msg: string) => {
		setStatus(msg);
		setTimeout(() => setStatus(null), 3000);
	};

	const fetchParams = async () => {
		try {
			const response = await fetch("http://localhost:5000/get/param");
			const data = await response.json();
			if (data.counter !== undefined) setCounter(data.counter);
			if (data.directory !== undefined) setDirectory(data.directory);
		} catch (error) {
			console.error("Error fetching params:", error);
		}
	};

	useEffect(() => {
		fetchParams();
	}, []);

	const handleAction = async (url: string, body?: object) => {
		try {
			const res = await fetch(url, {
				method: "POST",
				...(body && {
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(body),
				}),
			});
			const data = await res.json();
			if (data.status === "success") notify("Saved");
		} catch (e) {
			console.error(e);
		}
	};
	const saveClassification = () => {
		handleAction(`http://localhost:5000/save/${classification}`);
	};
	const sendCounter = () => {
		handleAction(`http://localhost:5000/set/counter/${counter}`);
	};
	const sendDirectory = () => {
		handleAction(
			`http://localhost:5000/set/directory/${encodeURIComponent(directory)}`,
		);
	};

	return (
		<Card>
			<h2 className="text-lg font-semibold text-gray-700 mb-2">
				Colector Control
			</h2>
			<div className="mb-4">
				<div className="mb-6 text-sm text-gray-500 grid items-center colect-control">
					<h3 className="text-sm font-semibold text-gray-500 uppercase">
						Counter:
					</h3>
					<input
						type="number"
						value={counter}
						onChange={(e) => setCounter(Number(e.target.value))}
						className="border rounded px-2 py-1 w-20 text-sm"
					/>
					<button onClick={sendCounter} className="rounded text-sm">
						{" "}
						{"->"}{" "}
					</button>
					<h3 className="text-sm font-semibold text-gray-500 uppercase">
						Directory:
					</h3>
					<input
						type="text"
						value={directory}
						onChange={(e) => setDirectory(e.target.value)}
						className="border rounded px-2 py-1 w-20 text-sm"
					/>
					<button onClick={sendDirectory} className="rounded text-sm">
						{" "}
						{"->"}{" "}
					</button>
					<h3 className="text-sm font-semibold text-gray-500 uppercase">
						Class:
					</h3>
					<input
						type="text"
						value={classification}
						onChange={(e) => setClassification(e.target.value)}
						className="border rounded px-2 py-1 w-20 text-sm"
					/>
					<button onClick={saveClassification} className="rounded text-sm">
						{" "}
						{"->"}{" "}
					</button>
				</div>
				{status && <p className="text-green-400 text-sm mb-2">{status}</p>}
			</div>
		</Card>
	);
};

export default ColectorCard;
