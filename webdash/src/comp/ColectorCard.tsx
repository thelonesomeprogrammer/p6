import type React from "react";
import { useEffect, useState } from "react";
import Card from "./Card";
import ToggleSwitch from "./ToggleSwitch";
import Select from "./Select";

const CLASSIFICATION_OPTIONS = ["OT", "UT", "N", "M", "PA"];

const ColectorCard: React.FC = () => {
	const [counter, setCounter] = useState<number>(0);
	const [directory, setDirectory] = useState<string>("");
	const [classification, setClassification] = useState<string>("OT");
	const [isCollecting, setIsCollecting] = useState<boolean>(false);
	const [collectionCount, setCollectionCount] = useState<number>(0);
	const [multiClassifications, setMultiClassifications] = useState<string[]>([]);

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

			const collectRes = await fetch("http://localhost:5000/get_collect");
			const collectData = await collectRes.json();
			setIsCollecting(collectData.collect);

			const countRes = await fetch("http://localhost:5000/get_collection_count");
			const countData = await countRes.json();
			setCollectionCount(countData.count);
		} catch (error) {
			console.error("Error fetching params:", error);
		}
	};

	useEffect(() => {
		fetchParams();
		const interval = setInterval(fetchParams, 2000);
		return () => clearInterval(interval);
	}, []);

	useEffect(() => {
		if (collectionCount > multiClassifications.length) {
			setMultiClassifications([
				...multiClassifications,
				...Array(collectionCount - multiClassifications.length).fill(
					classification,
				),
			]);
		}
	}, [collectionCount, classification]);

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
			if (data.status === "success") notify("Success");
			fetchParams();
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

	const toggleCollection = () => {
		const nextState = !isCollecting;
		setIsCollecting(nextState);
		handleAction(
			`http://localhost:5000/${nextState ? "start_collection" : "stop_collection"}`,
		);
	};

	const saveAll = () => {
		handleAction("http://localhost:5000/save_all", {
			classifications: multiClassifications.slice(0, collectionCount),
		});
		setMultiClassifications([]);
	};

	return (
		<Card>
		<div className="flex justify-between items-center mb-3">
			<h2 className="text-lg font-semibold text-gray-700 mb-2">
				Colector Control
			</h2>
					{/* Collection Toggle */}
					<div className="flex items-center gap-2">
						<span className="font-semibold uppercase text-[10px]">Collect</span>
						<ToggleSwitch isOn={isCollecting} handleToggle={toggleCollection} />
				</div>
			</div>
			<div className="mb-4">
				<div className="flex items-center gap-4 mb-4 text-sm text-gray-500">
					{/* Counter */}
					<div className="flex items-center gap-1">
						<span className="font-semibold uppercase text-[10px]">#</span>
						<input
							type="number"
							value={counter}
							onChange={(e) => setCounter(Number(e.target.value))}
							className="border rounded px-1 py-0.5 w-12 text-xs"
						/>
					</div>


					{/* Directory */}
					<div className="flex items-center gap-1 flex-1">
						<span className="font-semibold uppercase text-[10px]">Dir</span>
						<input
							type="text"
							value={directory}
							onChange={(e) => setDirectory(e.target.value)}
							className="border rounded px-2 py-0.5 flex-1 text-xs"
						/>
					</div>
				</div>

				{collectionCount > 0 && !isCollecting && (
					<div className="border-t pt-4 mt-4">
						<div className="flex justify-between items-center mb-3">
							<h4 className="text-xs font-bold text-gray-500 uppercase">
								Assign Classes ({collectionCount} runs)
							</h4>
						</div>
						<div className="grid grid-cols-2 gap-x-4 gap-y-2 max-h-48 overflow-y-auto mb-4 pr-1">
							{Array.from({ length: collectionCount }).map((_, i) => (
								<div key={i} className="flex items-center gap-2">
									<span className="text-xs font-mono text-gray-400 w-8">
										#{counter + i}:
									</span>
									<Select
										value={multiClassifications[i] || "OT"}
										onChange={(val) => {
											const newClasses = [...multiClassifications];
											newClasses[i] = val;
											setMultiClassifications(newClasses);
										}}
										options={CLASSIFICATION_OPTIONS}
										className="flex-1 py-1"
									/>
								</div>
							))}
						</div>
						<button
							onClick={saveAll}
							className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded text-sm font-semibold transition-colors"
						>
							Save All Collected Runs
						</button>
					</div>
				)}
			</div>
		</Card>
	);
};

export default ColectorCard;
