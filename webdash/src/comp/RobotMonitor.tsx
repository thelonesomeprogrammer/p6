import { useEffect, useState } from "react";
import Card from "./Card";
import { io } from "socket.io-client";


interface ModbusData {
	[key: string]: number;
}

function RobotMonitor() {

	const [modbusData, setModbusData] = useState<ModbusData | null>(null);
	const [connected, setConnected] = useState(false);

	useEffect(() => {
		const socket = io("http://localhost:5000");

		socket.on("connect", () => {
			setConnected(true);
			console.log("Connected to WebSocket");
		});

		socket.on("disconnect", () => {
			setConnected(false);
			console.log("Disconnected from WebSocket");
		});

		socket.on("modbus_data", (data: ModbusData) => {
			setModbusData(data);
		});

		return () => {
			socket.disconnect();
		};
	}, []);

	return (
		<div className="RobotMonitor p-8">
			<Card>
				<h1 className="text-2xl font-bold mb-4">Robot Monitor</h1>
				<p className="mb-4">
					Status:{" "}
					<span className={connected ? "text-green-500" : "text-red-500"}>
						{connected ? "Connected" : "Disconnected"}
					</span>
				</p>
				
				{modbusData ? (
					<div className="grid sm:grid-cols-2 gap-4">
						{Object.entries(modbusData).map(([key, value]) => (
							<div key={key} className="p-4 rounded bg-gray-50">
								<h3 className="text-sm font-semibold text-gray-500 uppercase">{key}</h3>
								<p className="text-xl font-mono">{value.toFixed(3)}</p>
							</div>
						))}
					</div>
				) : (
					<p>Waiting for data...</p>
				)}
			</Card>
		</div>
	);
}


export default RobotMonitor;
