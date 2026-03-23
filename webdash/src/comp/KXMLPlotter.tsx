import type React from "react";
import { useEffect, useState } from "react";
import { io } from "socket.io-client";
import Card from "./Card";
import Plot from "./Plot";
import ExpandToggleButton from "./ExpandToggleButton";

const KXMLPlotter: React.FC = () => {
	const [data, setData] = useState<any[]>([]);
	const [isOpen, setIsOpen] = useState<boolean>(true);

	const fetchData = async () => {
		try {
			const response = await fetch("http://localhost:5000/kxml_data?points=500");
			const raw = await response.json();
			setData(raw.kxml_data || []);
		} catch (error) {
			console.error("Error fetching KXML data:", error);
		}
	};

	useEffect(() => {
		const socket = io("http://localhost:5000");

		socket.on("runFinished", () => {
			console.log("Run finished, fetching KXML data...");
			fetchData();
		});

		return () => {
			socket.disconnect();
		};
	}, []);

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
