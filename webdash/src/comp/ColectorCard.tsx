import type React from "react";
import { useEffect, useState, useCallback } from "react";
import { socket } from "../socket";
import Card from "./Card";
import ToggleSwitch from "./ToggleSwitch";
import Select from "./Select";

const CLASSIFICATION_OPTIONS = ["N", "OT", "UT", "M", "PA"];

const ColectorCard: React.FC<{ className?: string }> = ({ className = "" }) => {
	const [counter, setCounter] = useState<number>(0);
	const [directory, setDirectory] = useState<string>("");
	const [classification, setClassification] = useState<string>("N");
	const [isCollecting, setIsCollecting] = useState<boolean>(false);
	const [collectionCount, setCollectionCount] = useState<number>(0);
	const [multiClassifications, setMultiClassifications] = useState<string[]>([]);

	const [status, setStatus] = useState<string | null>(null);

	const notify = useCallback((msg: string) => {
		setStatus(msg);
	}, []);

	useEffect(() => {
		if (!status) return;
		const timer = setTimeout(() => setStatus(null), 3000);
		return () => clearTimeout(timer);
	}, [status]);

	const fetchInitialData = useCallback(async (signal?: AbortSignal) => {
		try {
			const [paramRes, collectRes, countRes] = await Promise.all([
				fetch(`http://${window.location.hostname}:5000/get/param`, { signal }),
				fetch(`http://${window.location.hostname}:5000/get_collect`, { signal }),
				fetch(`http://${window.location.hostname}:5000/get_collection_count`, { signal }),
			]);

			const paramData = await paramRes.json();
			const collectData = await collectRes.json();
			const countData = await countRes.json();

			if (paramData.counter !== undefined) setCounter(paramData.counter);
			if (paramData.directory !== undefined) setDirectory(paramData.directory);
			setIsCollecting(collectData.collect);
			setCollectionCount(countData.count);
		} catch (error: any) {
			if (error.name === "AbortError") return;
			console.error("Error fetching initial data:", error);
		}
	}, []);

	useEffect(() => {
		const controller = new AbortController();
		fetchInitialData(controller.signal);

		const onParamsUpdated = (data: any) => {
			if (data.counter !== undefined) setCounter(data.counter);
			if (data.directory !== undefined) setDirectory(data.directory);
		};

		const onCollectionUpdated = (data: any) => {
			if (data.collect !== undefined) setIsCollecting(data.collect);
			if (data.count !== undefined) setCollectionCount(data.count);
		};

		socket.on("params_updated", onParamsUpdated);
		socket.on("collection_updated", onCollectionUpdated);

		return () => {
			socket.off("params_updated", onParamsUpdated);
			socket.off("collection_updated", onCollectionUpdated);
			controller.abort();
		};
	}, [fetchInitialData]);

	useEffect(() => {
		if (collectionCount > multiClassifications.length) {
			setMultiClassifications([
				...multiClassifications,
				...Array(collectionCount - multiClassifications.length).fill(
					classification,
				),
			]);
		}
	}, [collectionCount, classification, multiClassifications]);

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
			fetchInitialData();
		} catch (e) {
			console.error(e);
		}
	};
	const saveClassification = () => {
		handleAction(`http://${window.location.hostname}:5000/save/${classification}`);
	};
	const sendCounter = () => {
		handleAction(`http://${window.location.hostname}:5000/set/counter/${counter}`);
	};
	const sendDirectory = () => {
		handleAction(
			`http://${window.location.hostname}:5000/set/directory/${encodeURIComponent(directory)}`,
		);
	};

	const toggleCollection = () => {
		const nextState = !isCollecting;
		setIsCollecting(nextState);
		handleAction(
			`http://${window.location.hostname}:5000/${nextState ? "start_collection" : "stop_collection"}`,
		);
	};

	const saveAll = () => {
		handleAction(`http://${window.location.hostname}:5000/save_all`, {
			classifications: multiClassifications.slice(0, collectionCount),
		});
		setMultiClassifications([]);
	};

	return (
		<Card className={`flex flex-col ${className}`}>
			<div className="flex justify-between items-center">
				<h2 className="text-lg font-semibold text-gray-700">
					Collector Control
				</h2>
				{/* Collection Toggle */}
				<div className="flex items-center gap-2">
					<span className="font-semibold uppercase text-[10px]">Collect</span>
					<ToggleSwitch isOn={isCollecting} handleToggle={toggleCollection} />
				</div>
			</div>
			<div className="">
				<div className="flex items-center gap-4 text-sm text-gray-500">
					{/* Counter */}
					<div className="relative">
						<input
							id="counter-input"
							type="number"
							value={counter}
							onChange={(e) => setCounter(Number(e.target.value))}
							className="rounded text-gray-800 bg-white focus:ring-1 focus:ring-blue-500 outline-none transition-all w-20"
							placeholder=" "
							min={0}
							step={1}
							onBlur={sendCounter}
							onKeyDown={(e) => {
								if (e.key === "Enter") {
									sendCounter();
									e.currentTarget.blur();
								}
							}}
						/>
						<label
							htmlFor="counter-input"
							className="absolute left-1 top-0 text-[11px] font-bold text-gray-400 uppercase transition-all peer-placeholder-shown:top-3 peer-placeholder-shown:text-xs peer-focus:top-1 peer-focus:text-[9px] pointer-events-none"
						>
							Count
						</label>
					</div>


					{/* Directory */}
					<div className="relative">
						<input
							id="dir-input"
							type="text"
							value={directory}
							onChange={(e) => setDirectory(e.target.value)}
							onBlur={sendDirectory}
							onKeyDown={(e) => {
								if (e.key === "Enter") {
									sendDirectory();
									e.currentTarget.blur();
								}
							}}
							className="rounded text-gray-800 bg-white focus:ring-1 focus:ring-blue-500 outline-none transition-all w-48"
							placeholder=" "
						/>
						<label
							htmlFor="dir-input"
							className="absolute left-1 top-0 text-[11px] font-bold text-gray-400 uppercase transition-all peer-placeholder-shown:top-3 peer-placeholder-shown:text-xs peer-focus:top-1 peer-focus:text-[9px] pointer-events-none"
						>
							Save Directory
						</label>
					</div>

				</div>

				{collectionCount > 0 && (
					<div className="border-t border-gray-200">
						<div className="flex justify-between items-center">
							<h4 className="text-xs font-bold text-gray-500 uppercase">
								Assign Classes ({collectionCount} runs)
							</h4>
						</div>
						<div className="grid grid-cols-2 gap-x-4 gap-y-2 max-h-36 overflow-y-auto">
							{Array.from({ length: collectionCount }).map((_, i) => (
								<div key={i} className="flex items-center gap-2">
									<span className="text-xs font-mono text-gray-400 w-8">
										#{counter + i}:
									</span>
									<Select
										value={multiClassifications[i] || "N"}
										onChange={(val) => {
											const newClasses = [...multiClassifications];
											newClasses[i] = val;
											setMultiClassifications(newClasses);
										}}
										options={CLASSIFICATION_OPTIONS}
										className="flex-1 w-20"
									/>
								</div>
							))}
						</div>
						<button
							onClick={saveAll}
							className="w-full bg-green-600 hover:bg-green-700 text-white rounded text-sm font-semibold transition-colors"
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
