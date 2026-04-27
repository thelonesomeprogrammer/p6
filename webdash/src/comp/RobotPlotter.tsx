import type React from "react";
import { useEffect, useState, useCallback } from "react";
import { socket } from "../socket";
import Card from "./Card";
import Plot from "./Plot";
import ExpandToggleButton from "./ExpandToggleButton";

const RobotPlotter: React.FC = () => {
	const [data, setData] = useState<any[]>([]);
	const [isOpen, setIsOpen] = useState<boolean>(true);

	const fetchData = useCallback(async (signal?: AbortSignal) => {
		try {
			const response = await fetch(`http://${window.location.hostname}:5000/data?points=500`, { signal });
			const raw = await response.json();
			setData(raw.data || []);
		} catch (error: any) {
			if (error.name === "AbortError") return;
			console.error("Error fetching Robot data:", error);
		}
	}, []);

	useEffect(() => {
		const controller = new AbortController();
		
		// Initial fetch
		fetchData(controller.signal);

		const onRunFinished = () => {
			console.log("Run finished event received, fetching data...");
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
						Robot Path & Current Data
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
								yKeys={["TCP_x(mm)"]}
								title="TCP X (mm)"
								colors={["#8884d8"]}
							/>
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["TCP_y(mm)"]}
								title="TCP Y (mm)"
								colors={["#82ca9d"]}
							/>
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["TCP_z(mm)"]}
								title="TCP Z (mm)"
								colors={["#ffc658"]}
							/>
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["TCP_rx(mm)"]}
								title="TCP Rx (mm)"
								colors={["#ff7300"]}
							/>
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["TCP_ry(mm)"]}
								title="TCP Ry (mm)"
								colors={["#0088fe"]}
							/>
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["TCP_rz(mm)"]}
								title="TCP Rz (mm)"
								colors={["#00c49f"]}
							/>
							<Plot
								data={data}
								xKey="Time(ms)"
								yKeys={["Robot_I(A)"]}
								title="Robot Current (A)"
								colors={["#ff7300"]}
							/>
						</div>
					) : (
						<div className="py-10 text-center text-gray-300 animate-pulse text-sm">
							Awaiting Robot data...
						</div>
					)}
				</>
			)}
		</Card>
	);
};

export default RobotPlotter;
