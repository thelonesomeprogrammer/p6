import { useEffect, useState } from "react";
import { io } from "socket.io-client";
import Card from "./Card";

interface ModbusData {
	[key: string]: number;
}

function RobotMonitor() {
	const [modbusData, setModbusData] = useState<ModbusData | null>(null);
	const [connected, setConnected] = useState(false);

	useEffect(() => {
		const socket = io("http://localhost:5000");
		socket.on("connect", () => setConnected(true));
		socket.on("disconnect", () => setConnected(false));
		socket.on("modbus_data", (data: ModbusData) => setModbusData(data));
		return () => {
			socket.disconnect();
		};
	}, []);

	return (
		<div className="RobotMonitor">
			<Card className="">
				<h2 className="text-lg font-semibold text-gray-700 mb-2">
					Robot Monitor
				</h2>
				<p className="mb-6 text-sm font-light text-gray-500">
					Status:{" "}
					<span
						className={`font-medium ${connected ? "text-green-400" : "text-red-400"}`}
					>
						{connected ? "Active" : "Offline"}
					</span>
				</p>

				{modbusData ? (
					<div className="grid sm:grid-cols-2 gap-y-4">
						{Object.entries(modbusData).map(([key, value]) => (
							<div key={key} className="p-4 rounded bg-gray-50">
								<h3 className="text-sm font-semibold text-gray-500 uppercase">
									{key}
								</h3>
								<p className="text-xl font-mono">{value.toFixed(3)}</p>
							</div>
						))}
					</div>
				) : (
					<div className="py-10 text-center text-gray-300 animate-pulse text-sm">
						Awaiting connection...
					</div>
				)}
			</Card>
		</div>
	);
}

export default RobotMonitor;
