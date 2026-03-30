import { useEffect, useState } from "react";
import { socket } from "../socket";
import Card from "./Card";

interface RobotData {
	"TCP_x(mm)": number | null;
	"TCP_y(mm)": number | null;
	"TCP_z(mm)": number | null;
	"TCP_rx(mm)": number | null;
	"TCP_ry(mm)": number | null;
	"TCP_rz(mm)": number | null;
	"Robot_I(A)": number | null;
}

const MONITOR_KEYS: (keyof RobotData)[] = [
	"TCP_x(mm)",
	"TCP_y(mm)",
	"TCP_z(mm)",
	"TCP_rx(mm)",
	"TCP_ry(mm)",
	"TCP_rz(mm)",
	"Robot_I(A)",
];

function RobotMonitor({ className = "" }: { className?: string }) {
	const [modbusData, setModbusData] = useState<RobotData>({
		"TCP_x(mm)": null,
		"TCP_y(mm)": null,
		"TCP_z(mm)": null,
		"TCP_rx(mm)": null,
		"TCP_ry(mm)": null,
		"TCP_rz(mm)": null,
		"Robot_I(A)": null,
	});
	const [connected, setConnected] = useState(socket.connected);

	useEffect(() => {
		const onConnect = () => setConnected(true);
		const onDisconnect = () => setConnected(false);
		const onModbusData = (data: Partial<RobotData>) => {
			setModbusData((prev) => ({ ...prev, ...data }));
		};

		socket.on("connect", onConnect);
		socket.on("disconnect", onDisconnect);
		socket.on("modbus_data", onModbusData);

		return () => {
			socket.off("connect", onConnect);
			socket.off("disconnect", onDisconnect);
			socket.off("modbus_data", onModbusData);
		};
	}, []);


	return (
		<Card className={`flex flex-col ${className}`}>
			<div className="flex justify-between items-center">
				<h2 className="text-lg font-semibold text-gray-700">Robot Monitor</h2>
				<div className="flex items-center gap-2 text-xs">
					<span
						className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 animate-pulse" : "bg-red-400"}`}
					/>
					<span
						className={`font-medium ${connected ? "text-green-600" : "text-red-400"}`}
					>
						{connected ? "Active" : "Offline"}
					</span>
				</div>
			</div>
			<div className="grid grid-cols-2 gap-4 flex-1">
				{MONITOR_KEYS.map((key) => {
					const value = modbusData[key];
					return (
						<div
							key={key}
							className="rounded bg-gray-50 flex flex-col justify-center"
						>
							<h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
								{key}
							</h3>
							<p className="text-lg font-mono font-medium text-gray-800">
								{typeof value === "number" ? value.toFixed(3) : "---"}
							</p>
						</div>
					);
				})}
			</div>
		</Card>
	);
}

export default RobotMonitor;
