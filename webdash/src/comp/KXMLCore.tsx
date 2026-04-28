import type React from "react";
import Card from "./Card";
import Plot from "./Plot";
import ExpandToggleButton from "./ExpandToggleButton";

interface KXMLCoreProps {
	data: any[];
	isOpen: boolean;
	setIsOpen: (open: boolean) => void;
	isLoading?: boolean;
}

export const KXMLCore: React.FC<KXMLCoreProps> = ({
	data,
	isOpen,
	setIsOpen,
	isLoading,
}) => {
	return (
		<Card className="flex flex-col">
			<div className="flex justify-between items-center mb-4">
				<div className="flex items-center gap-2">
					<h2 className="text-lg font-semibold text-gray-700">
						Screw driving Data Graphs
					</h2>
					{isLoading && (
						<span className="text-[10px] animate-pulse text-blue-500 font-bold uppercase">
							Streaming...
						</span>
					)}
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

export default KXMLCore;
