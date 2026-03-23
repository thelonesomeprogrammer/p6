import type React from "react";
import { useEffect, useState } from "react";
import { io } from "socket.io-client";
import Card from "./Card";
import Plot from "./Plot";
import ExpandToggleButton from "./ExpandToggleButton";

const RobotPlotter: React.FC = () => {
	const [data, setData] = useState<any[]>([]);
	const [isOpen, setIsOpen] = useState<boolean>(true);

	const fetchData = async () => {
		try {
			const response = await fetch("http://localhost:5000/data?points=500");
			const raw = await response.json();
			setData(raw.data || []);
		} catch (error) {
			console.error("Error fetching Robot data:", error);
		}
	};

	useEffect(() => {
		const socket = io("http://localhost:5000");
		socket.on("runFinished", () => {
			console.log("Run finished event received, fetching data...");
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
