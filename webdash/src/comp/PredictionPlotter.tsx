import type React from "react";
import { useEffect, useState, useRef } from "react";
import { socket } from "../socket";
import Card from "./Card";
import Plot from "./Plot";
import ExpandToggleButton from "./ExpandToggleButton";

const PredictionPlotter: React.FC = () => {
	const [data, setData] = useState<any[]>([]);
	const [isOpen, setIsOpen] = useState<boolean>(true);
	const startTimeRef = useRef<number>(Date.now());

	useEffect(() => {
		const onPrediction = (pred: any) => {
			if (pred.regression) {
				const point = {
					time: (Date.now() - startTimeRef.current),
					...pred.regression,
				};
				setData((prev) => [...prev, point].slice(-100));
			}
		};

		const newScrew = () => {
			startTimeRef.current = Date.now();
			setData([]);
		}

		socket.on("prediction", onPrediction);
		socket.on("new_screw", newScrew);

		return () => {
			socket.off("prediction", onPrediction);
			socket.off("new_screw", newScrew);
		};
	}, []);

	return (
		<Card className="flex flex-col">
			<div className="flex justify-between items-center mb-4">
				<div className="flex items-center gap-2">
					<h2 className="text-lg font-semibold text-gray-700">
						Prediction Graphs
					</h2>
					<span className="text-[10px] animate-pulse text-blue-500 font-bold uppercase">
						Live
					</span>
				</div>
				<ExpandToggleButton
					isOpen={isOpen}
					onClick={() => setIsOpen(!isOpen)}
				/>
			</div>
			{isOpen && (
				<>
					{data.length > 0 ? (
						<div className="grid grid-cols-1 gap-4">
							<Plot
								data={data}
								xKey="time"
								yKeys={["remaining_angle"]}
								title="Remaining Angle (°)"
								colors={["#ff7300"]}
							/>
						</div>
					) : (
						<div className="py-10 text-center text-gray-300 animate-pulse text-sm">
							Awaiting prediction data...
						</div>
					)}
				</>
			)}
		</Card>
	);
};

export default PredictionPlotter;
