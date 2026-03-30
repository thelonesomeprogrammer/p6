import type React from "react";
import { useEffect, useState, useCallback } from "react";
import { socket } from "../socket";
import Card from "./Card";
import Plot from "./Plot";
import ExpandToggleButton from "./ExpandToggleButton";

const KXMLPlotter: React.FC = () => {
	const [data, setData] = useState<any[]>([]);
	const [isOpen, setIsOpen] = useState<boolean>(true);

	const fetchData = useCallback(async (signal?: AbortSignal) => {
		try {
			const response = await fetch("http://localhost:5000/kxml_data?points=500", { signal });
			const raw = await response.json();
			setData(raw.kxml_data || []);
		} catch (error: any) {
			if (error.name === "AbortError") return;
			console.error("Error fetching KXML data:", error);
		}
	}, []);

	useEffect(() => {
		const controller = new AbortController();

		// Initial fetch
		fetchData(controller.signal);

		const onRunFinished = () => {
			console.log("Run finished, fetching KXML data...");
			fetchData(controller.signal);
		};

		socket.on("runFinished", onRunFinished);

		return () => {
			socket.off("runFinished", onRunFinished);
			controller.abort();
		};
	}, [fetchData]);

	return (
		<Card className="flex flex-col">
			<div className="flex justify-between items-center mb-4">
				<div className="flex items-center gap-2">
					<h2 className="text-lg font-semibold text-gray-700">
						Screw driving Data Graphs
					</h2>
				</div>
				<ExpandToggleButton
					isOpen={isOpen}
					onClick={() => setIsOpen(!isOpen)}
				/>
			</div>
			{isOpen && (
				<>
					{data.length > 0 ? (
						<div className="grid grid-cols-2 gap-4">
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["Torque(Nm)"]}
								title="Torque (Nm)"
							/>
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["Nset(1/min)"]}
								title="Speed (1/min)"
								colors={["#82ca9d"]}
							/>
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["Current(V)"]}
								title="Current (V)"
								colors={["#ffc658"]}
							/>
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["Depth(mm)"]}
								title="Depth (mm)"
								colors={["#ff7300"]}
							/>
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["Angle(°)"]}
								title="Angle (°)"
								colors={["#8884d8"]}
							/>
						</div>
					) : (
						<div className="py-10 text-center text-gray-300 animate-pulse text-sm">
							Awaiting KXML data...
						</div>
					)}
				</>
			)}
		</Card>
	);
};

export default KXMLPlotter;
