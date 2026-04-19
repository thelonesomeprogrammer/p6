import type React from "react";
import Card from "./Card";

export interface PredictionResult {
	prediction: string;
	probabilities: Record<string, number>;
	window_percent: number;
	remaining_angle?: number;
}

interface ScrewCoreProps {
	prediction: PredictionResult | null;
	isLoading?: boolean;
	error?: string | null;
	className?: string;
}

export const ScrewCore: React.FC<ScrewCoreProps> = ({
	prediction,
	isLoading,
	error,
	className = "",
}) => {
	const remaining = prediction?.remaining_angle ?? 3100;
	const percentIn = Math.max(
		0,
		Math.min(100, ((3100 - remaining) / 3100) * 100),
	);

	const hasFinalClass = prediction && prediction.prediction;

	return (
		<Card className={`flex flex-col min-w-[180px] h-full ${className}`}>
			<div className="flex justify-between items-center mb-4">
				<h2 className="text-sm font-semibold text-gray-700">Screw Animation</h2>
				{isLoading && (
					<span className="text-[10px] animate-pulse text-blue-500 font-bold uppercase">
						Updating...
					</span>
				)}
			</div>

			<div className="flex-1 relative bg-gray-50 rounded-lg border border-gray-100 overflow-hidden min-h-[140px] flex flex-col items-center justify-center">
				<div className="absolute top-1/2 left-1/2 -translate-x-1/2 w-12 h-1/2 bg-[#8b4513] border-t-2 border-[#5d2e0d] shadow-[inset_0_4px_8px_rgba(0,0,0,0.2)]">
					<div
						className="absolute inset-0 opacity-10"
						style={{
							backgroundImage:
								"repeating-linear-gradient(90deg, transparent, transparent 15px, #000 15px, #000 16px), repeating-linear-gradient(0deg, transparent, transparent 10px, #000 10px, #000 11px)",
						}}
					/>
					<div className="absolute top-0 left-1/2 -translate-x-1/2 w-5 h-1.5 bg-[#4a250b] rounded-full blur-[1px]" />
				</div>

				<div
					className="absolute left-1/2 w-6"
					style={{
						top: "50%",
						height: "80px",
						transform: `translateX(-50%) translateY(${-80 + percentIn * 0.75}px)`,
						transition:
							"transform 2.5s cubic-bezier(0.45, 0.05, 0.55, 0.95), opacity 0.5s ease-in-out",
						zIndex: 10,
						opacity: hasFinalClass && prediction.prediction !== "M" ? 1 : 0,
						pointerEvents: hasFinalClass ? "auto" : "none",
					}}
				>
					<div className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-2 bg-gradient-to-r from-gray-400 via-gray-100 to-gray-400 rounded-t-sm border border-gray-500 shadow-sm">
						<div
							className="absolute top-1/2 left-1/2 -translate-y-1/2 h-1.5 bg-gray-600/40 rounded-full"
							style={{
								width: `${Math.abs(Math.cos(percentIn * 0.1)) * 4 + 2}px`,
								left: "50%",
								transform: "translateX(-50%)",
							}}
						/>
					</div>
					<div className="absolute top-[2px] left-1/2 -translate-x-1/2 w-4 h-1.5 bg-gray-400 border-x border-gray-500" />
					<div className="absolute top-[3.5px] left-1/2 -translate-x-1/2 w-3 h-[65px] bg-gradient-to-r from-gray-400 via-gray-300 to-gray-400 border-x border-gray-500 overflow-hidden">
						<div
							className="absolute inset-0 opacity-40"
							style={{
								backgroundImage:
									"repeating-linear-gradient(-20deg, transparent, transparent 3px, #444 3px, #444 5px)",
								backgroundPosition: `0 ${percentIn * 2}px`,
								transition:
									"background-position 2.5s cubic-bezier(0.45, 0.05, 0.55, 0.95)",
							}}
						/>
					</div>
					<div className="absolute top-[68.5px] left-1/2 -translate-x-1/2 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[12px] border-t-gray-400" />
				</div>

				{!hasFinalClass && (
					<div className="text-xs text-gray-400 italic font-medium uppercase tracking-wider animate-pulse">
						Awaiting classification
					</div>
				)}

				{error && (
					<div className="absolute top-2 left-2 right-2 text-[10px] text-red-500 bg-white/80 p-1 rounded border border-red-100">
						{error}
					</div>
				)}
			</div>

			{hasFinalClass && (
				<div className="mt-3 flex items-center justify-between px-1">
					<div className="flex flex-col">
						<span className="text-[10px] font-bold text-gray-400 uppercase">
							Predicted State
						</span>
						<span
							className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase w-fit ${
								prediction.prediction === "N"
									? "bg-green-100 text-green-700"
									: prediction.prediction === "M"
										? "bg-blue-100 text-blue-700"
										: prediction.prediction === "OT"
											? "bg-orange-100 text-orange-700"
											: "bg-red-100 text-red-700"
							}`}
						>
							{typeof prediction.prediction === "object"
								? (prediction.prediction as any).prediction
								: prediction.prediction}
						</span>
					</div>
					<div className="flex flex-col items-end">
						<span className="text-[10px] font-bold text-gray-400 uppercase">
							Progress
						</span>
						<span className="text-xs font-mono text-gray-600">
							{percentIn.toFixed(1)}%
						</span>
					</div>
				</div>
			)}
		</Card>
	);
};

export default ScrewCore;
